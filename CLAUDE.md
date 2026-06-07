# itamar-weiss.com

Next.js (App Router) site deployed on Vercel. Migrated from Jekyll/GitHub Pages.
See `README.md` for the full project layout.

## Content model

- **Blog posts** live in `content/posts/*.md` as `YYYY-MM-DD-slug.md` with
  frontmatter (`title`, `date`, `categories`, `comments`). They are rendered
  statically by `app/blog/[slug]/page.tsx` and served at `/blog/<slug>/`.
- **Pages** (`About`, `Portfolio`) live in `content/pages/*.md`.
- **Legacy URLs**: every old Jekyll URL (e.g.
  `/drones/2024/12/07/how-does-a-drone-fly.html`) is permanently redirected to
  its new `/blog/<slug>/` URL. The redirects are generated in `lib/redirects.ts`
  from each post's `legacyUrl`, computed in `lib/posts.ts`. If you change a
  post's filename, date, or categories, the legacy redirect changes too — keep
  `lib/posts.ts` as the single source of truth for URL logic.

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
