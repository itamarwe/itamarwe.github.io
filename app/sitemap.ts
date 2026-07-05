import type { MetadataRoute } from "next";
import { getAllPosts } from "@/lib/posts";
import { site } from "@/lib/site";

export default function sitemap(): MetadataRoute.Sitemap {
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

  return [...staticPages, ...posts];
}
