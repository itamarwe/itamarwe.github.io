// Everything the FPV viewer renders is fetched from CloudFront at runtime
// (published from the fpv-drone-strikes-lebanon-dataset repo via
// `npm run publish-web`). These bases are safe to use on the client.
const CDN = "https://d2fioemadmrru3.cloudfront.net";

export const CDN_BASE = CDN;
export const SCENE_BASE = `${CDN}/scenes`;
export const THUMB_BASE = `${CDN}/thumbnails`;
export const DATA_URL = `${CDN}/data/videos.json`;
export const REDIRECTS_URL = `${CDN}/data/redirects.json`;
