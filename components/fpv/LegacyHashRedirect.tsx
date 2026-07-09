"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { slugify } from "@/lib/fpv/slug";

// The viewer used to live at a static hash-routed mount: /fpv/#/video/<file>,
// /fpv/#/scene/<file>. Those fragments never reach the server, so any legacy
// link now loads the gallery — this rehomes it client-side to the clean URL.
export function LegacyHashRedirect() {
  const router = useRouter();
  useEffect(() => {
    const raw = window.location.hash;
    if (!raw || raw === "#" || raw === "#/") return;
    const hash = raw.replace(/^#\/?/, "");
    const [view, ...rest] = hash.split("/");
    const arg = decodeURIComponent(rest.join("/"));
    if ((view === "video" || view === "scene") && arg) {
      router.replace(`/fpv/${view}/${slugify(arg)}/`);
    }
  }, [router]);
  return null;
}
