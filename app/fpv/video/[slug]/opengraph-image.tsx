import { getVideoBySlug } from "@/lib/fpv/data";
import { fpvOgImage, OG_CONTENT_TYPE, OG_SIZE } from "@/lib/fpv/og";

export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;
export const alt = "FPV drone-strike video";

export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const v = await getVideoBySlug(slug);
  return fpvOgImage(v, "video");
}
