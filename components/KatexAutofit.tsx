"use client";

import { useEffect } from "react";

/**
 * Makes KaTeX display equations responsive without a horizontal scrollbar: if an
 * equation is wider than its container, shrink its font-size just enough to fit.
 * Because KaTeX lays out in em units, scaling the font scales width *and* height
 * proportionally — so the math stays fully visible and the layout doesn't break.
 */
export default function KatexAutofit() {
  useEffect(() => {
    const fit = () => {
      const blocks =
        document.querySelectorAll<HTMLElement>(".post-content .katex-display");
      blocks.forEach((el) => {
        el.style.fontSize = ""; // reset to natural size before measuring
        const avail = el.clientWidth;
        const needed = el.scrollWidth;
        if (needed > avail) {
          const base = parseFloat(getComputedStyle(el).fontSize);
          // 0.96 leaves a little breathing room for sub/superscripts that poke out
          el.style.fontSize = `${base * (avail / needed) * 0.96}px`;
        }
      });
    };

    fit();
    window.addEventListener("resize", fit);
    // Re-fit once web fonts have loaded, since metrics change after that.
    if (document.fonts?.ready) document.fonts.ready.then(fit).catch(() => {});
    return () => window.removeEventListener("resize", fit);
  }, []);

  return null;
}
