import type { Redirect } from "next/dist/lib/load-custom-routes";
import { getAllPosts } from "./posts";

/**
 * Permanent redirects from every legacy Jekyll URL to its new clean URL.
 *
 * The legacy URLs included a `.html` suffix and, for a few posts, comma
 * characters (a Jekyll quirk where `categories: a, b` was space-split into the
 * path segments `a,/b`). Reproducing them exactly here means no inbound link or
 * indexed search result breaks after the migration.
 */
export const legacyRedirects: Redirect[] = getAllPosts().map((post) => ({
  source: post.legacyUrl,
  destination: post.url,
  permanent: true,
}));
