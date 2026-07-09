// Slug derivation, kept byte-for-byte in sync with the dataset repo's
// tools/build_web_data.mjs so a video file name maps to the same slug the
// published manifest uses. Client-safe (no Node APIs) so the legacy
// hash-URL redirect can compute it in the browser.
export function slugify(value: string): string {
  const stem = value.replace(/\.[^./]+$/, "");
  return (
    stem
      .replace(/[^a-zA-Z0-9._-]+/g, "_")
      .replace(/^_+|_+$/g, "")
      .slice(0, 120) || "video"
  );
}
