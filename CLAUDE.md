# itamarwe.github.io

Jekyll site published via GitHub Pages.

## Always verify links before adding them

This is a static site, so a typo in an internal link is a dead link in production. Before adding any link in a markdown file:

- **External links**: confirm the URL resolves (WebFetch or WebSearch).
- **Internal links**: confirm the target file exists and the URL matches Jekyll's actual generated path. The default permalink is `/:categories/:year/:month/:day/:title.html`, so the URL depends on the post's `categories:` frontmatter. Cross-check against an existing post's link to confirm the path format.
- **Watch the `categories:` field**: writing `categories: ai, code` as a comma-separated string does **not** produce `/ai/code/...` — Jekyll needs a YAML list (`categories: [ai, code]` or block style) or space-separated values.

## Pull request workflow

Once a pull request for a working branch has been merged, it is closed — pushing more commits to that branch will **not** reopen or update it. 

### After merging a branch:

1. **Create a new branch** from `master` for the next set of changes
2. **Make commits** to the new branch
3. **Open a new pull request** for the new branch

Do not continue pushing commits to a branch whose PR has already been merged.

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

5. **Embed in Jekyll** with a plain `<video>` tag — autoplay/loop/muted/playsinline works in all modern browsers without JavaScript:
   ```html
   <video src="/img/folder/clip.mp4" autoplay loop muted playsinline style="width:100%"></video>
   ```
