import type { MetadataRoute } from "next";
import { getAllPosts } from "@/lib/posts";
import { site } from "@/lib/site";
import { getVideos } from "@/lib/fpv/data";
import { sceneHref, videoHref } from "@/lib/fpv/paths";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticPages: MetadataRoute.Sitemap = [
    { url: `${site.url}/`, changeFrequency: "weekly", priority: 1 },
    { url: `${site.url}/about/`, changeFrequency: "monthly", priority: 0.7 },
    { url: `${site.url}/solar-system/`, changeFrequency: "yearly", priority: 0.3 },
    { url: `${site.url}/photo-geolocation/`, changeFrequency: "yearly", priority: 0.3 },
    // The FPV viewer tracks a dataset that keeps growing, so it changes often.
    { url: `${site.url}/fpv/`, changeFrequency: "weekly", priority: 0.5 },
  ];

  const posts: MetadataRoute.Sitemap = getAllPosts().map((post) => ({
    url: `${site.url}${post.url}`,
    lastModified: new Date(post.date),
    changeFrequency: "yearly",
    priority: 0.8,
  }));

  // One entry per video, plus one per reconstructed 3D scene. Best-effort: if
  // the published manifest can't be fetched at build time, still emit the rest.
  let fpv: MetadataRoute.Sitemap = [];
  try {
    const videos = await getVideos();
    fpv = videos.flatMap((v) => {
      const entries: MetadataRoute.Sitemap = [
        { url: `${site.url}${videoHref(v.slug)}`, changeFrequency: "monthly", priority: 0.5 },
      ];
      if (v.scenePath) {
        entries.push({
          url: `${site.url}${sceneHref(v.slug)}`,
          changeFrequency: "monthly",
          priority: 0.6,
        });
      }
      return entries;
    });
  } catch {
    fpv = [];
  }

  return [...staticPages, ...posts, ...fpv];
}
