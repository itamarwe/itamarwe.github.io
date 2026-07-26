import { NextResponse, type NextRequest } from "next/server";
import { REMOVED_URL } from "@/lib/fpv/config";
import type { RemovedManifest } from "@/lib/fpv/types";

// Videos withdrawn from the dataset are gone for good — there is no successor to
// redirect to (that is what data/redirects.json is for). Next has no way to set a
// status code from a page, and notFound() would answer 404, which crawlers retry
// for months. Middleware is the only layer that can answer 410 Gone, which tells
// them to drop the URL. The dataset publishes independently of this site, so the
// list is fetched rather than baked into the build.

const TTL_MS = 5 * 60 * 1000;

let cache: { at: number; ids: Set<string> } | null = null;

async function removedIds(): Promise<Set<string>> {
  if (cache && Date.now() - cache.at < TTL_MS) return cache.ids;
  try {
    const res = await fetch(REMOVED_URL, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const payload = (await res.json()) as RemovedManifest;
    cache = { at: Date.now(), ids: new Set(payload.removed.map((r) => r.id)) };
  } catch {
    // Fail open — a manifest hiccup must not take down live pages. Stamp the
    // cache either way so a persistent failure doesn't refetch on every request.
    cache = { at: Date.now(), ids: cache?.ids ?? new Set() };
  }
  return cache.ids;
}

export async function middleware(request: NextRequest) {
  // /fpv/{video,scene}/<slug>/ — and /<slug>/opengraph-image, which shares it.
  const slug = request.nextUrl.pathname.split("/").filter(Boolean)[2];
  if (!slug) return NextResponse.next();

  const removed = await removedIds();
  if (!removed.has(slug)) return NextResponse.next();

  return new NextResponse("410 Gone — this entry was removed from the dataset.\n", {
    status: 410,
    headers: {
      "content-type": "text/plain; charset=utf-8",
      "cache-control": "public, max-age=3600",
    },
  });
}

export const config = {
  matcher: ["/fpv/video/:path*", "/fpv/scene/:path*"],
};
