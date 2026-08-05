# design-sync notes — itamar-weiss.com

- This repo is a Next.js **website**, not a component package. The user scoped the
  sync to **styles & tokens only** — the converter runs in tokens-only mode via a
  synthetic empty entry (`.design-sync/ds-entry.mjs`, `window.ItamarWeiss` is
  intentionally empty). Zero components discovered is **by design**, not a bug
  (src-root resolves to `lib/`, which has no `.tsx`).
- `cfg.cssEntry` points at a **generated** file: run `cfg.buildCmd` (sass compile
  of `styles/globals.scss` + concat with `.design-sync/tokens.css`, tokens first)
  before every converter/driver run, or the build fails on a missing file.
- `.design-sync/tokens.css` is authored: it mirrors the SCSS variables in
  `styles/globals.scss` and the figure accent palette in `CLAUDE.md` as CSS custom
  properties (SCSS vars are compile-time and wouldn't otherwise ship). **If
  globals.scss variables or the CLAUDE.md palette change, update tokens.css to
  match** — nothing regenerates it.
- Fonts: Geist Sans/Mono variable woff2 come from `node_modules/geist` (same
  binaries next/font uses). **Doto** (site-title dot-matrix font) is a Google Font
  loaded at runtime via `next/font/google`, so its latin-subset variable woff2 is
  committed at `.design-sync/fonts/Doto-Variable.woff2` (OFL license). The
  `--font-geist-sans`/`--font-geist-mono`/`--font-doto` custom properties that
  next/font injects at runtime are defined statically in tokens.css instead.
- Verification: tokens-only → the render check is vacuous (0 previews). The look
  was verified by screenshotting a scratch page (`ds-bundle/.style-check.html`,
  dot-prefixed → never uploaded, wiped on rebuild) exercising the header, type,
  code block, link, blockquote, and all accent swatches — Doto/Geist loaded and
  every color matched.

## Known render warns

- (none — 0 previews)

## Re-sync risks

- `tokens.css` duplicates values from `styles/globals.scss` + `CLAUDE.md`; it can
  silently go stale if the site theme changes (see above).
- Doto woff2 is a pinned **latin-only** subset fetched 2026-08-05; re-fetch from
  Google Fonts if coverage needs grow.
- The sass compile happens outside the converter (`buildCmd`) — a re-sync that
  skips it uploads the previous compile's CSS.
- No components are synced; if the user later wants components (Header/Footer are
  Next-coupled; ProfileDots is canvas-based), that's a scope change requiring
  real work, not just config.
