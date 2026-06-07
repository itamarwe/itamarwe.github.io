/**
 * In-browser *instance-ish* segmentation with SAM (Segment Anything).
 *
 * Transformers.js 4.x ships SamModel/SamProcessor but no automatic
 * "everything" mask generator (generate_crop_boxes is a stub), so we roll a
 * lightweight one here: encode the image once, prompt a regular grid of
 * foreground points, keep the best mask per point, then greedily de-duplicate
 * overlapping masks (NMS by IoU). Each surviving region gets its own colour, so
 * adjacent buildings tend to come out as distinct blobs.
 *
 * SAM is class-agnostic — it finds regions, it doesn't label them — so there's
 * no sky/buildings/etc. legend here, just N coloured regions.
 */
import { SamModel, AutoProcessor, RawImage } from '@huggingface/transformers'

// SAM's vision encoder always runs at 1024², so feeding a smaller image only
// trims mask post-processing cost. We work the masks at this resolution; the
// overlay <img> scales up to the photo (uniform, stays aligned).
const SAM_DIM = 512
const POINTS_PER_SIDE = 16     // 16×16 = 256 candidate prompts
const POINT_BATCH = 32         // points per decoder run (memory vs round-trips)
const IOU_NMS = 0.7            // drop a mask if it overlaps a kept one beyond this
const MIN_AREA_FRAC = 0.0015   // ignore specks
const MAX_AREA_FRAC = 0.92     // ignore whole-image "background" masks
const SCORE_MIN = 0.80         // SAM's predicted-IoU quality gate

// One model+processor per id, loaded on first use (WebGPU → WASM fallback).
const samPromises = new Map()
function getSam(modelId, onProgress) {
  if (samPromises.has(modelId)) return samPromises.get(modelId)
  const promise = (async () => {
    const hasWebGPU = typeof navigator !== 'undefined' && 'gpu' in navigator
    const load = (device) => Promise.all([
      SamModel.from_pretrained(modelId, { device, progress_callback: onProgress }),
      AutoProcessor.from_pretrained(modelId, { progress_callback: onProgress }),
    ])
    try {
      const [model, processor] = await load(hasWebGPU ? 'webgpu' : 'wasm')
      return { model, processor }
    } catch (err) {
      if (!hasWebGPU) throw err
      const [model, processor] = await load('wasm')
      return { model, processor }
    }
  })()
  samPromises.set(modelId, promise)
  promise.catch(() => samPromises.delete(modelId))
  return promise
}

/** Distinct, readable colours via golden-angle hue spacing. */
function hslColor(i) {
  const h = (i * 137.508) % 360
  const s = 0.62, l = 0.55
  const c = (1 - Math.abs(2 * l - 1)) * s
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1))
  const m = l - c / 2
  let r = 0, g = 0, b = 0
  if (h < 60) { r = c; g = x } else if (h < 120) { r = x; g = c }
  else if (h < 180) { g = c; b = x } else if (h < 240) { g = x; b = c }
  else if (h < 300) { r = x; b = c } else { r = c; b = x }
  return [Math.round((r + m) * 255), Math.round((g + m) * 255), Math.round((b + m) * 255)]
}

export async function segmentImageSAM(url, { modelId, onProgress } = {}) {
  const { model, processor } = await getSam(modelId, onProgress)

  let image = await RawImage.fromURL(url)
  const scale = Math.min(1, SAM_DIM / Math.max(image.width, image.height))
  if (scale < 1) {
    image = await image.resize(Math.round(image.width * scale), Math.round(image.height * scale))
  }
  const w = image.width, h = image.height
  const area = w * h

  onProgress?.({ status: 'progress', sam: 'embedding' })
  const inputs = await processor(image)
  const { image_embeddings, image_positional_embeddings } = await model.get_image_embeddings(inputs)

  // Regular grid of foreground points, in the (resized) image's pixel space.
  const pts = []
  for (let iy = 0; iy < POINTS_PER_SIDE; iy++) {
    const y = Math.round(((iy + 0.5) / POINTS_PER_SIDE) * h)
    for (let ix = 0; ix < POINTS_PER_SIDE; ix++) {
      pts.push([Math.round(((ix + 0.5) / POINTS_PER_SIDE) * w), y])
    }
  }

  // Each candidate: { data: Uint8(w*h), area, score }.
  const candidates = []
  for (let start = 0; start < pts.length; start += POINT_BATCH) {
    const batch = pts.slice(start, start + POINT_BATCH)
    // input_points shape [batch=1, point_batch=B, points_per_mask=1, 2]
    const grid = [batch.map((p) => [p])]
    const input_points = processor.reshape_input_points(grid, inputs.original_sizes, inputs.reshaped_input_sizes)
    const out = await model({ image_embeddings, image_positional_embeddings, input_points })

    const masks = await processor.post_process_masks(out.pred_masks, inputs.original_sizes, inputs.reshaped_input_sizes)
    const mt = masks[0]                       // bool tensor [B, 3, h, w]
    const B = mt.dims[0], C = mt.dims[1]
    const md = mt.data
    const iou = out.iou_scores.data           // [B, C]
    const plane = h * w

    for (let b = 0; b < B; b++) {
      let best = 0
      for (let c = 1; c < C; c++) if (iou[b * C + c] > iou[b * C + best]) best = c
      const score = iou[b * C + best]
      if (score < SCORE_MIN) continue
      const base = (b * C + best) * plane
      let a = 0
      const data = new Uint8Array(plane)
      for (let i = 0; i < plane; i++) {
        if (md[base + i]) { data[i] = 1; a++ }
      }
      if (a < MIN_AREA_FRAC * area || a > MAX_AREA_FRAC * area) continue
      candidates.push({ data, area: a, score })
    }
    onProgress?.({ status: 'progress', sam: 'decoding', progress: Math.min(100, Math.round(((start + B) / pts.length) * 100)) })
  }

  // NMS: prefer higher-quality, then larger; drop anything that mostly overlaps
  // a region we already kept.
  candidates.sort((p, q) => (q.score - p.score) || (q.area - p.area))
  const kept = []
  for (const cand of candidates) {
    let dup = false
    for (const k of kept) {
      let inter = 0
      const a = cand.data, b = k.data
      for (let i = 0; i < a.length; i++) if (a[i] && b[i]) inter++
      const iou = inter / (cand.area + k.area - inter)
      if (iou > IOU_NMS) { dup = true; break }
    }
    if (!dup) kept.push(cand)
  }

  // Paint largest first so smaller regions stay visible on top.
  kept.sort((p, q) => q.area - p.area)
  const rgba = new Uint8ClampedArray(area * 4)
  kept.forEach((region, idx) => {
    const [r, g, b] = hslColor(idx)
    const data = region.data
    for (let i = 0, j = 0; i < data.length; i++, j += 4) {
      if (data[i]) {
        rgba[j] = r; rgba[j + 1] = g; rgba[j + 2] = b; rgba[j + 3] = 255
      }
    }
  })

  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  canvas.getContext('2d').putImageData(new ImageData(rgba, w, h), 0, 0)

  return {
    url: canvas.toDataURL('image/png'),
    width: w,
    height: h,
    groups: [],
    instanceCount: kept.length,
    kind: 'sam',
    modelId,
  }
}
