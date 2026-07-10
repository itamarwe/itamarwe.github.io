import "server-only";
import { DATA_URL } from "./config";
import type { Dataset, VideoRecord } from "./types";

// Fetch the published manifest server-side. Cached for 5 minutes so new videos
// / scenes show up within minutes of a `publish-web` without a redeploy, and so
// generateMetadata / the page / the OG image share one request per revalidation.
export async function getDataset(): Promise<Dataset> {
  const res = await fetch(DATA_URL, { next: { revalidate: 300 } });
  if (!res.ok) throw new Error(`FPV manifest HTTP ${res.status}`);
  return (await res.json()) as Dataset;
}

export async function getVideos(): Promise<VideoRecord[]> {
  const data = await getDataset();
  return [...data.videos].sort((a, b) =>
    a.date < b.date ? 1 : a.date > b.date ? -1 : 0,
  );
}

export async function getVideoBySlug(slug: string): Promise<VideoRecord | null> {
  const videos = await getVideos();
  return videos.find((v) => v.slug === slug) ?? null;
}

export async function getSceneVideos(): Promise<VideoRecord[]> {
  const videos = await getVideos();
  return videos.filter((v) => v.scenePath);
}

export function videoTitle(v: VideoRecord): string {
  return v.description || v.videoFile;
}

export function videoSubtitle(v: VideoRecord): string {
  return [v.date, v.town].filter(Boolean).join(" · ");
}
