/**
 * In-browser semantic segmentation for the uploaded photo.
 *
 * Runs a SegFormer model via Transformers.js (ONNX, WebGPU with a WASM
 * fallback). Models are fetched from the Hugging Face hub on first use and
 * cached by the browser, so there's no server component. Several models are
 * offered (see SEG_MODELS) so they can be compared side by side: ADE20K
 * (general 150-class scenes) and Cityscapes (street-scene trained, usually a
 * better fit for urban photos), at a range of sizes (b0 fast → b5 accurate).
 *
 * Each model's fine-grained labels are collapsed into a handful of readable
 * groups (sky / buildings / vegetation / road-ground / people / vehicles /
 * other), each painted a distinct colour. The result is returned as a single
 * RGBA PNG data URL the photo pane overlays on top of the image.
 */
import { pipeline, env, RawImage } from '@huggingface/transformers'
import { segmentImageSAM } from './sam'

// Always pull model files from the HF hub — we ship none locally.
env.allowLocalModels = false

/**
 * Selectable models, in rough fast→accurate order. `id` is our stable key;
 * `modelId` is the Hugging Face repo. ADE20K = general scenes; Cityscapes =
 * trained on street-level city imagery (cleaner buildings/road/sky for the
 * kind of photos this tool targets).
 */
export const SEG_MODELS = [
  { id: 'ade-b0',   label: 'ADE20K · b0 (fast)',        modelId: 'Xenova/segformer-b0-finetuned-ade-512-512' },
  { id: 'ade-b4',   label: 'ADE20K · b4',               modelId: 'Xenova/segformer-b4-finetuned-ade-512-512' },
  { id: 'city-b0',  label: 'Cityscapes · b0 (fast)',    modelId: 'Xenova/segformer-b0-finetuned-cityscapes-1024-1024' },
  { id: 'city-b1',  label: 'Cityscapes · b1',           modelId: 'Xenova/segformer-b1-finetuned-cityscapes-1024-1024' },
  { id: 'city-b4',  label: 'Cityscapes · b4',           modelId: 'Xenova/segformer-b4-finetuned-cityscapes-1024-1024' },
  { id: 'city-b5',  label: 'Cityscapes · b5 (best)',    modelId: 'Xenova/segformer-b5-finetuned-cityscapes-1024-1024' },
  // SAM is class-agnostic instance-ish segmentation: each region gets its own
  // colour (no sky/buildings legend). Routed to a separate code path below.
  { id: 'sam',      label: 'SAM · auto (per-region)',   modelId: 'Xenova/slimsam-77-uniform', kind: 'sam' },
]
const MODEL_BY_ID = Object.fromEntries(SEG_MODELS.map((m) => [m.id, m]))
const DEFAULT_MODEL = SEG_MODELS[0].id

// Cap the resolution we actually segment + paint, for speed and memory. The
// overlay is scaled back up to the photo's size by the pane (uniform scale, so
// it stays aligned). 1024px on the long edge is plenty for an overlay.
const MAX_DIM = 1024

/** Display order + colours for the grouped categories (also drives the legend). */
export const SEG_GROUPS = [
  { id: 'sky',         label: 'Sky',           color: [77, 166, 255] },
  { id: 'buildings',   label: 'Buildings',     color: [232, 103, 74] },
  { id: 'vegetation',  label: 'Vegetation',    color: [76, 175, 80] },
  { id: 'road_ground', label: 'Road / ground', color: [150, 150, 150] },
  { id: 'people',      label: 'People',        color: [255, 212, 0] },
  { id: 'vehicles',    label: 'Vehicles',      color: [192, 98, 224] },
  { id: 'other',       label: 'Other',         color: [92, 107, 122] },
]
const COLOR_BY_ID = Object.fromEntries(SEG_GROUPS.map((g) => [g.id, g.color]))

// Label → group, matched by synonym token. Covers both ADE20K (names are
// semicolon/comma-separated synonym lists, e.g. "car;auto;automobile") and
// Cityscapes (single words: building, vegetation, terrain, rider, motorcycle…).
// We split on those separators and test each token; first matching group wins,
// unmatched → 'other'.
const GROUP_KEYWORDS = [
  ['sky',         ['sky']],
  ['vegetation',  ['tree', 'grass', 'plant', 'flower', 'palm', 'flora', 'vegetation']],
  ['buildings',   ['building', 'edifice', 'house', 'skyscraper', 'tower', 'hovel', 'hut', 'booth', 'wall']],
  ['road_ground', ['road', 'route', 'sidewalk', 'pavement', 'earth', 'ground', 'floor', 'flooring', 'path', 'runway', 'dirt', 'sand', 'field', 'terrain']],
  ['people',      ['person', 'individual', 'someone', 'somebody', 'rider']],
  ['vehicles',    ['car', 'auto', 'automobile', 'truck', 'bus', 'van', 'minibike', 'motorbike', 'motorcycle', 'bicycle', 'bike', 'boat', 'airplane', 'aeroplane', 'ship', 'train']],
]

function labelToGroup(label) {
  if (!label) return 'other'
  const tokens = label.toLowerCase().split(/[;,]/).map((s) => s.trim())
  for (const [group, words] of GROUP_KEYWORDS) {
    if (tokens.some((t) => words.includes(t))) return group
  }
  return 'other'
}

// One pipeline instance per model, loaded on first use. WebGPU when available,
// otherwise WASM. Promises are cached (keyed by model id) so switching back to
// a previously-loaded model is instant and concurrent calls share one load.
const segmenterPromises = new Map()
function getSegmenter(modelId, onProgress) {
  const model = MODEL_BY_ID[modelId] || MODEL_BY_ID[DEFAULT_MODEL]
  if (segmenterPromises.has(model.id)) return segmenterPromises.get(model.id)
  const promise = (async () => {
    const hasWebGPU = typeof navigator !== 'undefined' && 'gpu' in navigator
    try {
      return await pipeline('image-segmentation', model.modelId, {
        device: hasWebGPU ? 'webgpu' : 'wasm',
        progress_callback: onProgress,
      })
    } catch (err) {
      if (!hasWebGPU) throw err
      // WebGPU init can fail on some machines/drivers — fall back to WASM.
      return await pipeline('image-segmentation', model.modelId, {
        device: 'wasm',
        progress_callback: onProgress,
      })
    }
  })()
  segmenterPromises.set(model.id, promise)
  // Don't cache a rejected load — let a later attempt retry from scratch.
  promise.catch(() => segmenterPromises.delete(model.id))
  return promise
}

/**
 * Segment an image (object URL or data URL) into the grouped categories with
 * the chosen model. Returns { url, width, height, groups, modelId } where url
 * is a colored RGBA PNG data URL and groups is the list of group ids actually
 * present (for the legend).
 */
export async function segmentImage(url, { modelId = DEFAULT_MODEL, onProgress } = {}) {
  const model = MODEL_BY_ID[modelId] || MODEL_BY_ID[DEFAULT_MODEL]
  if (model.kind === 'sam') {
    // Return our stable id (not the HF repo) so the legend resolves the label.
    const out = await segmentImageSAM(url, { modelId: model.modelId, onProgress })
    return { ...out, modelId: model.id }
  }
  const segmenter = await getSegmenter(modelId, onProgress)

  let image = await RawImage.fromURL(url)
  const scale = Math.min(1, MAX_DIM / Math.max(image.width, image.height))
  if (scale < 1) {
    image = await image.resize(Math.round(image.width * scale), Math.round(image.height * scale))
  }
  const w = image.width, h = image.height

  // NB: don't pass an explicit `subtask` — in transformers 4.2.0 that path
  // leaves the post-processor as a bare string (a library bug: "fn is not a
  // function"). Omitting it lets the pipeline auto-resolve, which correctly
  // binds SegFormer's `post_process_semantic_segmentation`.
  const output = await segmenter(image)

  const rgba = new Uint8ClampedArray(w * h * 4)
  const present = new Set()
  for (const seg of output) {
    const group = labelToGroup(seg.label)
    present.add(group)
    const [r, g, b] = COLOR_BY_ID[group]
    const mask = seg.mask.data
    for (let i = 0, j = 0; i < mask.length; i++, j += 4) {
      if (mask[i] > 0) {
        rgba[j] = r
        rgba[j + 1] = g
        rgba[j + 2] = b
        rgba[j + 3] = 255
      }
    }
  }

  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  canvas.getContext('2d').putImageData(new ImageData(rgba, w, h), 0, 0)

  return {
    url: canvas.toDataURL('image/png'),
    width: w,
    height: h,
    groups: SEG_GROUPS.filter((g) => present.has(g.id)).map((g) => g.id),
    modelId,
  }
}
