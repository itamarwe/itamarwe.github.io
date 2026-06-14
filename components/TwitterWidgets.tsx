"use client";

import { useEffect } from "react";

/**
 * Upgrades any `<blockquote class="twitter-tweet">` placed in post markdown into
 * the rich X/Twitter embed (with its video) by loading X's widgets.js on demand.
 * If the script is blocked or JS is off, the blockquote degrades to a normal
 * attributed quote linking to the original post. Only loads when a tweet is
 * actually present on the page.
 */
declare global {
  interface Window {
    twttr?: { widgets?: { load?: () => void } };
  }
}

export default function TwitterWidgets() {
  useEffect(() => {
    if (!document.querySelector(".twitter-tweet")) return;
    const id = "twitter-wjs";
    const load = () => window.twttr?.widgets?.load?.();
    if (document.getElementById(id)) {
      load();
      return;
    }
    const s = document.createElement("script");
    s.id = id;
    s.async = true;
    s.src = "https://platform.twitter.com/widgets.js";
    s.onload = load;
    document.body.appendChild(s);
  }, []);

  return null;
}
