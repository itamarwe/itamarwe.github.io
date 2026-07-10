import { ImageResponse } from "next/og";
import { THUMB_BASE } from "./config";
import type { VideoRecord } from "./types";
import { videoSubtitle, videoTitle } from "./data";

export const OG_SIZE = { width: 1200, height: 630 };
export const OG_CONTENT_TYPE = "image/png";

// Fetch a thumbnail and inline it as a data URL. Only PNG/JPEG are embedded —
// satori can't reliably rasterize WebP, so an unsupported type falls back to a
// text-only card rather than 500-ing the whole OG route.
async function loadImage(url: string | null): Promise<string | null> {
  if (!url) return null;
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    const type = res.headers.get("content-type") || "";
    if (!/^image\/(png|jpe?g)$/.test(type)) return null;
    const buf = Buffer.from(await res.arrayBuffer());
    return `data:${type};base64,${buf.toString("base64")}`;
  } catch {
    return null;
  }
}

function thumbUrl(v: VideoRecord): string | null {
  // Prefer the source thumbnail (usually JPEG) over the responsive WebP set.
  if (v.thumbnailUrl) return v.thumbnailUrl;
  if (v.thumbWidths?.length) {
    return `${THUMB_BASE}/${v.slug}/${v.thumbWidths[v.thumbWidths.length - 1]}.webp`;
  }
  return null;
}

// Social share card: the clip's thumbnail with a title/description caption,
// composed at 1200×630. Used by both the video and scene routes.
export async function fpvOgImage(v: VideoRecord | null, kind: "video" | "scene") {
  const title = v ? videoTitle(v) : "FPV Drone-Strike Dataset";
  const subtitle = v ? videoSubtitle(v) : "Hezbollah FPV drone strikes from Lebanon";
  const badge = kind === "scene" ? "3D reconstruction" : "Video";
  const img = v ? await loadImage(thumbUrl(v)) : null;

  return new ImageResponse(
    (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          width: "100%",
          height: "100%",
          background: "#000000",
          color: "#ededed",
          fontFamily: "sans-serif",
        }}
      >
        <div
          style={{
            display: "flex",
            position: "relative",
            width: "100%",
            height: "430px",
            background: "#0b0d0f",
          }}
        >
          {img ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={img}
              alt=""
              width={1200}
              height={430}
              style={{ width: "1200px", height: "430px", objectFit: "cover" }}
            />
          ) : null}
          <div
            style={{
              display: "flex",
              position: "absolute",
              top: "24px",
              left: "48px",
              padding: "6px 16px",
              borderRadius: "999px",
              background: "rgba(0,0,0,0.6)",
              border: "1px solid rgba(255,255,255,0.35)",
              color: "#ffffff",
              fontSize: "24px",
            }}
          >
            {badge}
          </div>
        </div>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            flex: 1,
            padding: "0 48px",
            borderTop: "3px solid #3291ff",
          }}
        >
          <div
            style={{
              display: "flex",
              fontSize: "46px",
              fontWeight: 700,
              color: "#ffffff",
              lineHeight: 1.15,
            }}
          >
            {title}
          </div>
          {subtitle ? (
            <div style={{ display: "flex", fontSize: "26px", color: "#a1a1a1", marginTop: "12px" }}>
              {subtitle}
            </div>
          ) : null}
        </div>
      </div>
    ),
    OG_SIZE,
  );
}
