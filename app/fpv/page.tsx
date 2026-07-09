import type { Metadata } from "next";
import { getVideos } from "@/lib/fpv/data";
import { Gallery } from "@/components/fpv/Gallery";

export const revalidate = 300;

const TITLE = "FPV Drone-Strike Dataset Viewer";
const DESCRIPTION =
  "Browse Hezbollah FPV drone-strike clips from Lebanon — search the gallery, read auto-annotated flight timelines, and orbit reconstructed 3-D attack paths, right in the browser.";

export const metadata: Metadata = {
  title: { absolute: TITLE },
  description: DESCRIPTION,
  alternates: { canonical: "/fpv/" },
  openGraph: { title: TITLE, description: DESCRIPTION, url: "/fpv/", type: "website" },
};

export default async function FpvGalleryPage() {
  const videos = await getVideos();
  return <Gallery videos={videos} />;
}
