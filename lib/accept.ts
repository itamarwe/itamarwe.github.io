/**
 * Markdown content negotiation (acceptmarkdown.com).
 *
 * An agent that wants markdown sends `Accept: text/markdown` (optionally with
 * q-values). We serve the markdown variant only when the request *explicitly*
 * names `text/markdown` and doesn't rank `text/html` above it — a bare
 * wildcard Accept (what curl and browsers effectively send) must keep
 * getting HTML, so wildcards never count as asking for markdown.
 *
 * Kept dependency-free and framework-free so it runs identically in the Edge
 * middleware and under `node --test`.
 */

interface MediaRange {
  type: string;
  q: number;
}

/** Parse an Accept header into media ranges with their q-values. */
export function parseAccept(header: string): MediaRange[] {
  return header
    .split(",")
    .map((part) => {
      const [rawType, ...params] = part.trim().split(";");
      const type = rawType.trim().toLowerCase();
      let q = 1;
      for (const p of params) {
        const [key, value] = p.split("=").map((s) => s.trim().toLowerCase());
        if (key === "q") {
          const parsed = Number(value);
          if (Number.isFinite(parsed)) q = Math.min(Math.max(parsed, 0), 1);
        }
      }
      return { type, q };
    })
    .filter((r) => r.type.length > 0);
}

/** Effective q-value for a concrete media type, most-specific match wins. */
function qualityFor(ranges: MediaRange[], fullType: string): number {
  const [mainType] = fullType.split("/");
  let best: { specificity: number; q: number } | null = null;
  for (const r of ranges) {
    let specificity: number;
    if (r.type === fullType) specificity = 2;
    else if (r.type === `${mainType}/*`) specificity = 1;
    else if (r.type === "*/*") specificity = 0;
    else continue;
    if (!best || specificity > best.specificity) best = { specificity, q: r.q };
  }
  return best ? best.q : 0;
}

/**
 * Should this request get the markdown variant instead of HTML?
 *
 * True only when `text/markdown` is explicitly listed with q > 0 and HTML is
 * not preferred over it (an explicit tie goes to markdown — a client that
 * bothers to name `text/markdown` is asking for it).
 */
export function prefersMarkdown(acceptHeader: string | null): boolean {
  if (!acceptHeader) return false;
  const ranges = parseAccept(acceptHeader);
  const explicitMd = ranges.find((r) => r.type === "text/markdown");
  if (!explicitMd || explicitMd.q <= 0) return false;
  return explicitMd.q >= qualityFor(ranges, "text/html");
}
