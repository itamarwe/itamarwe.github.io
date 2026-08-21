/**
 * Which request paths have a markdown variant, negotiable via
 * `Accept: text/markdown` (served by app/md/[[...path]]/route.ts). Used by
 * the Edge middleware, so this must stay dependency-free (no fs): it names
 * the same shapes markdownForPath() in lib/agent-content.ts resolves —
 * home, the standalone pages, and /blog/<slug>/ (existing or not, so unknown
 * slugs can answer a markdown 404).
 */
export function hasMarkdownVariant(pathname: string): boolean {
  return /^\/(?:|(?:about|contact|privacy)\/?|blog(?:\/[^/]+)?\/?)$/.test(pathname);
}
