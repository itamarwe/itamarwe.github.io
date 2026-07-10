import type { Metadata } from "next";
import { notFound } from "next/navigation";
import {
  getVideos,
  getVideoBySlug,
  videoSubtitle,
  videoTitle,
} from "@/lib/fpv/data";
import { videoHref } from "@/lib/fpv/paths";
import { VideoView } from "@/components/fpv/VideoView";

export const revalidate = 300;

type Params = { params: Promise<{ slug: string }> };

export async function generateStaticParams() {
  const videos = await getVideos();
  return videos.map((v) => ({ slug: v.slug }));
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { slug } = await params;
  const v = await getVideoBySlug(slug);
  if (!v) return {};
  const title = videoTitle(v);
  const sub = videoSubtitle(v);
  const description = `Hezbollah FPV drone-strike clip${sub ? ` — ${sub}` : ""}. Watch it with an auto-annotated flight timeline.`;
  const url = videoHref(v.slug);
  return {
    title,
    description,
    alternates: { canonical: url },
    openGraph: { title, description, url, type: "video.other" },
    twitter: { card: "summary_large_image" },
  };
}

export default async function VideoPage({ params }: Params) {
  const { slug } = await params;
  const v = await getVideoBySlug(slug);
  if (!v) notFound();
  return <VideoView video={v} />;
}
