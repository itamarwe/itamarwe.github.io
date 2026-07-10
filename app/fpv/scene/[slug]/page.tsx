import type { Metadata } from "next";
import { notFound } from "next/navigation";
import {
  getSceneVideos,
  getVideoBySlug,
  videoSubtitle,
  videoTitle,
} from "@/lib/fpv/data";
import { sceneHref } from "@/lib/fpv/paths";
import { SceneView } from "@/components/fpv/SceneView";

export const revalidate = 300;

type Params = { params: Promise<{ slug: string }> };

export async function generateStaticParams() {
  const videos = await getSceneVideos();
  return videos.map((v) => ({ slug: v.slug }));
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { slug } = await params;
  const v = await getVideoBySlug(slug);
  if (!v) return {};
  const title = videoTitle(v);
  const sub = videoSubtitle(v);
  const description = `3-D reconstruction of a Hezbollah FPV drone strike${sub ? ` — ${sub}` : ""}. Orbit the attack path and read its speed/height flight profile.`;
  const url = sceneHref(v.slug);
  return {
    title: `${title} — 3D scene`,
    description,
    alternates: { canonical: url },
    openGraph: { title, description, url, type: "website" },
    twitter: { card: "summary_large_image" },
  };
}

export default async function ScenePage({ params }: Params) {
  const { slug } = await params;
  const v = await getVideoBySlug(slug);
  if (!v || !v.scenePath) notFound();
  return <SceneView video={v} />;
}
