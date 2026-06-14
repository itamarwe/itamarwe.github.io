# itamar-weiss.com

Next.js (App Router) site deployed on Vercel. Migrated from Jekyll/GitHub Pages.
See `README.md` for the full project layout.

## Content model

- **Blog posts** live in `content/posts/*.md` as `YYYY-MM-DD-slug.md` with
  frontmatter (`title`, `date`, `categories`, `comments`, and optional `image`
  for the social-share card — see "Social-share images" below). They are rendered
  statically by `app/blog/[slug]/page.tsx` and served at `/blog/<slug>/`.
- **Pages** (`About`, `Portfolio`) live in `content/pages/*.md`.
- **Legacy URLs**: every old Jekyll URL (e.g.
  `/drones/2024/12/07/how-does-a-drone-fly.html`) is permanently redirected to
  its new `/blog/<slug>/` URL. The redirects are generated in `lib/redirects.ts`
  from each post's `legacyUrl`, computed in `lib/posts.ts`. If you change a
  post's filename, date, or categories, the legacy redirect changes too — keep
  `lib/posts.ts` as the single source of truth for URL logic.

## Writing new blog posts (voice & visual style)

The house style for explainer posts is set by the FPV acoustic-detection post
(`content/posts/2026-06-09-designing-a-mic-array-for-acoustic-drone-detection.md`)
and the Gaussian-splatting post. When writing a new post, match them:

- **Voice**: first person, direct, and personal — "I kept running into…", "the part
  that made it click for me…". Open with the concrete problem or a hook, not a
  definition. Technically dense but conversational; bold the key claim in a
  paragraph rather than padding. Short sections with plain `##` headings.
- **Illustrations (3Blue1Brown / Manim style)**: clean diagrams on a near-black
  background (`#0e1116` or `#000`), accent palette cyan `#3fc1ff`, gold `#ffd166`,
  green `#7CFC8A`, red `#ff5a5a`, purple `#b48cff`, muted text `#8b95a5`. Generate
  them with matplotlib or Manim in a venv (see "Generated figures & animations")
  and save under `public/img/<post>/`. Every major concept gets one figure.
- **Animations** where motion explains it better than a still (a training loop
  converging, a beam sweeping): render an `.mp4` and embed with a plain autoplay/
  loop/muted `<video>` (see "Capturing demo videos" / "Generated figures").
- **Interactive demos** where the reader benefits from poking at it (sweeping a
  parameter, orbiting a 3-D scene): build a self-contained page under
  `public/<name>/` and embed via `<iframe class="viz-frame">` (see "Interactive 3D
  visualizations"). Verify it renders headlessly before committing.
- Prefer a non-redundant set: each figure / animation / demo should teach something
  the others don't.
- **Keep the simulation / figure-generation code in the repo.** Commit every script
  that produced a figure, animation, or numeric result under `research/<post>/`
  (`sim/` for plots & data, `scenes/` for Manim) with a short `README.md` — see
  `research/mic-array/` and `research/gaussian-splatting/`. The committed PNGs/MP4s
  live in `public/img/<post>/`; the code that regenerates them lives in `research/`.
  Make output paths repo-relative (derive from `__file__`), not absolute home paths.
- **Be honest about what a visual is.** If a figure or animation is a simplified or
  illustrative stand-in rather than the real computation, say so in the post (a brief
  parenthetical) and in the script's docstring.

## Always verify links before adding them

A dead internal link is a dead link in production. Before adding any link in a
markdown file:

- **External links**: confirm the URL resolves (WebFetch or WebSearch).
- **Internal links**: link to the clean URL, `/blog/<slug>/` (slug = the post
  filename without the date prefix and extension, case preserved), or `/about/`
  / `/portfolio/`. Cross-check against an existing post to confirm the format.

## Pull request workflow

**Always branch and PR — never push directly to `master`.**

For every change, no matter how small:

1. **Start from an up-to-date `master`**: check out `master` and `git pull` before creating a new branch.
2. **Create a new branch** from `master`.
3. **Make commits** to that branch.
4. **Open a pull request** — do not merge yourself; leave it for the user to review and merge.
5. **Leave the working directory clean**: after opening the PR, switch back to `master`, pull the latest, and confirm `git status` shows nothing unexpected.

Once a PR is merged, that branch is closed. Do not push further commits to it — create a new branch for the next set of changes.

## Capturing demo videos from a running web app

To embed demo videos in a post, use Playwright to record the live app rather than recreating it. General pattern:

1. **Expose internals** — patch the app's JS to set `window.__camera`, `window.__controls`, or whatever handles you need for programmatic control, then restart the dev server.

2. **Scaffold a capture script** (`/tmp/capture/capture.js`) with this structure:
   - Launch Chromium with `--use-gl=angle` (required for WebGL headless)
   - Create a context with `recordVideo` pointing to a temp dir
   - On page load: hide UI chrome with `addStyleTag`, inject a fake CSS cursor div (`window.__moveCursor(x, y)`)
   - Run `setup(page)` to set initial camera/state, then `waitForTimeout(SETUP_SECS * 1000)`
   - Run `animate(page, clipSecs)` — drive the camera via `page.evaluate` + `requestAnimationFrame` loop
   - After recording: trim the setup period and encode with ffmpeg: `ffmpeg -ss SETUP_SECS -i input.webm -c:v libx264 -pix_fmt yuv420p -t clipSecs output.mp4`

3. **Camera geometry** — always reason about where the Sun/light is before placing the camera. To show a day/night terminator, position the camera *perpendicular* to the light-source→object axis, not behind the object.

4. **Install Remotion skill** for programmatic video generation as an alternative: `npx skills add remotion-dev/skills`. Remotion + React Three Fiber works for recreating 3D scenes from scratch, but Playwright capture is faster when a real app already exists.

5. **Embed in a post** with a plain `<video>` tag in the markdown (raw HTML is
   supported) — autoplay/loop/muted/playsinline works in all modern browsers
   without JavaScript. Put the file under `public/img/...`:
   ```html
   <video src="/img/folder/clip.mp4" autoplay loop muted playsinline style="width:100%"></video>
   ```

## Interactive 3D visualizations (Three.js)

For 3blue1brown-style interactive diagrams, build a **self-contained HTML page**
under `public/<name>/` and embed it with an `<iframe>` — the established pattern,
see `public/pnp/` and `public/mic-array-viz/`:

- **Vendor Three.js locally** (copy `public/pnp/vendor/`) — no runtime CDN. Wire it
  with an `importmap` pointing at `./vendor/three.module.js` and `./vendor/addons/`.
- Pure-black `#000` background, `OrbitControls` (with damping), `CSS2DRenderer` for
  HTML labels. Keep all the math in plain JS so it recomputes live on interaction.
- Embed with `<iframe class="viz-frame" loading="lazy" src="/<name>/page.html">` and
  add a scoped `<style>` block **in the post markdown** (rehype-raw passes raw
  `<style>` through — there is no sanitizer in the pipeline). Give it a desktop
  `aspect-ratio:16/10` and a `@media (max-width:600px)` rule with a taller `3/4`
  frame plus compact control panels so it stays usable on phones.

## Generated figures & animations

- Work in a Python venv (`numpy scipy matplotlib manim`). Match the dark palette
  used across the visuals: background `#0e1116` (or `#000`), text `#ededed`,
  accents cyan `#3fc1ff`, gold `#ffd166`, green `#7CFC8A`, red `#ff5a5a`. Save PNGs
  under `public/img/<post>/`.
- **Manim**: no LaTeX is installed, so use `Text(...)`, never `Tex`/`MathTex`.
  Render with `manim -qm --format=mp4` and embed the result as a `<video>` (above).

## Social-share images

Every post emits an OpenGraph/Twitter image. Frontmatter takes an optional
`image:` (absolute site path, e.g. `/img/<post>/social.png`); it falls back to
`DEFAULT_OG_IMAGE` (`/img/profile.jpg`) in `lib/posts.ts`. When a post sets a custom
`image`, `app/blog/[slug]/page.tsx` upgrades the Twitter card to
`summary_large_image`. Make the card **1200×630** on a pure-black background, with
the post title and one strong visualization from the post — generate it like any
other figure and save it under `public/img/<post>/`.

## Verifying visuals headlessly

There is no display and browser-CDN downloads are blocked, but a Chromium binary
ships at `/opt/pw-browsers/chromium-*/chrome-linux/chrome`. Serve the site
(`cd public && python -m http.server PORT`) and screenshot:

```
chrome --headless=new --no-sandbox --use-gl=angle --use-angle=swiftshader \
  --enable-unsafe-swiftshader --window-size=1280,760 --virtual-time-budget=6000 \
  --screenshot=out.png "http://localhost:PORT/<name>/page.html"
```

For numeric correctness of a JS visualization, port its core math to a small Node
script and diff the outputs against the Python reference — don't trust the render
alone.
