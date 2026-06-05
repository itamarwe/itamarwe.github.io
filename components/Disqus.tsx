"use client";

import { useEffect, useRef } from "react";
import { site } from "@/lib/site";

/**
 * Disqus comments embed. Mirrors the old Jekyll `_includes/disqus.html`, which
 * rendered the thread on any post with `comments: true`.
 */
export default function Disqus() {
  const loaded = useRef(false);

  useEffect(() => {
    if (loaded.current) return;
    loaded.current = true;
    const d = document;
    const s = d.createElement("script");
    s.src = `https://${site.disqusShortname}.disqus.com/embed.js`;
    s.setAttribute("data-timestamp", String(Date.now()));
    (d.head || d.body).appendChild(s);
  }, []);

  return (
    <>
      <div id="disqus_thread" />
      <noscript>
        Please enable JavaScript to view the{" "}
        <a href="https://disqus.com/?ref_noscript">comments powered by Disqus.</a>
      </noscript>
    </>
  );
}
