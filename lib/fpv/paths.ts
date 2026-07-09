// Clean URL builders for the FPV viewer. Slug-based, no #/ prefix, trailing
// slash to match the site's `trailingSlash: true` convention. Safe on both
// server and client (pure string helpers).
export function galleryHref(): string {
  return "/fpv/";
}

export function videoHref(slug: string): string {
  return `/fpv/video/${slug}/`;
}

export function sceneHref(slug: string): string {
  return `/fpv/scene/${slug}/`;
}
