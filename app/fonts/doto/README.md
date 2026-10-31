# Doto

The Latin variable WOFF2 is bundled locally so `next build` does not fetch or
parse a Google Fonts response. This avoids the intermittent Doto loader failure
seen in the production build on September 26, 2026.

- Family: Doto, normal style, weights 100–900; default square-dot design.
- Source: [Google Fonts CSS](https://fonts.googleapis.com/css2?family=Doto:wght@100..900&display=swap), fetched with a modern browser user agent.
- File: [Google Fonts Latin WOFF2](https://fonts.gstatic.com/s/doto/v3/t5t6IRMbNJ6TQG7Il_EKPqP9zTnvqouBWhoxrW5O.woff2).
- License: SIL Open Font License 1.1, included in `OFL.txt` from the
  [Google Fonts repository](https://raw.githubusercontent.com/google/fonts/main/ofl/doto/OFL.txt).

`app/layout.tsx` loads this file through `next/font/local`, retaining the
`--font-doto` CSS variable and font preloading for the site and FPV headers.
