// Record the three social-media source clips (gallery / video / scene) from
// the live viewer, each at TWO viewports:
//   - 1600x900  (16:9, encoded to 1280x720 for Twitter/X)
//   - 1080x1080 (native square layout, encoded 1:1 for LinkedIn)
// The app is responsive, so the square take is a real square layout, not a crop.
//
// Env:
//   BASE      viewer origin+path        (default https://www.itamarweiss.com/fpv)
//   SLUG      demo clip                 (default the Biranit / Iron Dome strike)
//   FLIGHT_T  seek time (s) for the video take — the first flight segment
//   OUT       output dir                (default ./out/social-src)
//   PW_CHROME optional Chromium executablePath override
//
// Run via build_social.sh, which also trims + encodes the 8 final MP4s.
import pw from "playwright";
import fs from "node:fs";
const { chromium } = pw;

const BASE = (process.env.BASE || "https://www.itamarweiss.com/fpv").replace(/\/$/, "");
const SLUG = process.env.SLUG || "2026-05-26_anti_drone_platform_barashit.mp4";
const FLIGHT_T = Number(process.env.FLIGHT_T || 8.2);
const OUT = process.env.OUT || "./out/social-src";
if (!process.env.ONLY) fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.PW_CHROME || undefined,
  args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
         "--ignore-gpu-blocklist", "--enable-webgl", "--autoplay-policy=no-user-gesture-required"],
});

async function record(name, W, H, setup, action) {
  const dir = `${OUT}/${name}`;
  fs.mkdirSync(dir, { recursive: true });
  const ctx = await browser.newContext({
    viewport: { width: W, height: H }, deviceScaleFactor: 1,
    recordVideo: { dir, size: { width: W, height: H } },
  });
  const page = await ctx.newPage();
  page.on("console", (m) => { if (m.type() === "error") console.log(`[${name}] ERR`, m.text()); });
  const hideBars = () => page.addStyleTag({
    content: `::-webkit-scrollbar{width:0;height:0}html{scrollbar-width:none}`,
  }).catch(() => {});
  await setup(page, hideBars);
  await action(page);
  await ctx.close();
  const webm = fs.readdirSync(dir).find((f) => f.endsWith(".webm"));
  console.log(name, "->", webm);
}

// ---- Gallery: scroll, search, filter (action ≈ 13 s, keep last 13) ---------
const gallerySetup = async (page, hideBars) => {
  await page.goto(`${BASE}/#/`, { waitUntil: "domcontentloaded" });
  await hideBars();
  await page.waitForSelector(".video-card", { timeout: 20000 });
  await page.waitForFunction(() => {
    const imgs = [...document.querySelectorAll(".video-card img")].slice(0, 9);
    return imgs.length >= 6 && imgs.every((i) => i.complete && i.naturalWidth > 0);
  }, { timeout: 25000 }).catch(() => {});
  await sleep(600);
};
const galleryAction = async (page) => {
  const smoothScroll = (max, dur) => page.evaluate(async ({ max, dur }) => {
    const y0 = window.scrollY, start = performance.now();
    await new Promise((res) => {
      const step = (t) => { const k = Math.min((t - start) / dur, 1);
        window.scrollTo(0, y0 + (max - y0) * (0.5 - 0.5 * Math.cos(k * Math.PI)));
        k < 1 ? requestAnimationFrame(step) : res(); };
      requestAnimationFrame(step);
    });
  }, { max, dur });
  await sleep(500);
  await smoothScroll(1100, 3200);                        // browse down
  await sleep(500);
  await smoothScroll(0, 1400);                           // back to the toolbar
  await sleep(300);
  const search = page.locator('input[type="search"]');   // live search
  await search.click().catch(() => {});
  await search.pressSequentially("merkava", { delay: 110 }).catch(() => {});
  await sleep(1400);
  await search.fill("").catch(() => {});                 // clear
  await sleep(500);
  const btn = page.getByRole("button", { name: /3D scenes/i });  // filter
  if (await btn.count()) await btn.first().click().catch(() => {});
  await sleep(900);
  await smoothScroll(600, 1800);
  await sleep(700);
};

// ---- Video: seek to the first flight segment and let it play (keep last 10.5)
const videoSetup = async (page, hideBars) => {
  await page.goto(`${BASE}/#/video/${SLUG}`, { waitUntil: "domcontentloaded" });
  await hideBars();
  await page.waitForSelector("video", { timeout: 20000 });
  await page.waitForFunction(() => {
    const v = document.querySelector("video");
    return v && v.readyState >= 2;
  }, { timeout: 25000 }).catch(() => {});
  await page.evaluate(async (t) => {
    window.scrollTo(0, 0);
    const v = document.querySelector("video");
    if (v) { v.muted = true; v.currentTime = t; try { await v.play(); } catch {} }
  }, FLIGHT_T);
  await sleep(400);
};
const videoAction = async () => { await sleep(10200); };

// ---- Scene: playback + a slow there-and-back orbit (keep last 12) ----------
const sceneSetup = async (page, hideBars) => {
  await page.goto(`${BASE}/#/scene/${SLUG}`, { waitUntil: "domcontentloaded" });
  await hideBars();
  await page.waitForFunction(() => {
    const st = document.querySelector(".scene-status");
    const cv = document.querySelector(".canvas-holder canvas");
    return cv && (!st || !st.textContent);
  }, { timeout: 60000 }).catch(() => {});
  await sleep(800);
};
// The scene plays start -> end TWICE per take. The player's own semantics make
// this reliable: at the end the play button flips back to "Play", and clicking
// it again resets the timeline to t0 (k.t>=t1-.05 -> k.t=t0 in SceneView).
const sceneAction = async (page) => {
  const stage = await page.$(".scene-stage");
  const box = stage ? await stage.boundingBox()
                    : { x: 120, y: 210, width: 900, height: 460 };
  const cy = box.y + box.height * 0.52;
  const drag = async (fromK, toK, steps, lift) => {
    await page.mouse.move(box.x + box.width * fromK, cy);
    await page.mouse.down();
    for (let i = 0; i <= steps; i++) {
      const k = fromK + (toK - fromK) * (i / steps);
      await page.mouse.move(box.x + box.width * k,
                            cy - Math.sin((i / steps) * Math.PI) * lift);
      await sleep(55);
    }
    await page.mouse.up();
  };
  const BTN = ".scene-controls .play-btn";
  const clickPlay = () => page.evaluate((s) => document.querySelector(s)?.click(), BTN);
  const waitPlaying = () => page.waitForFunction(
    (s) => document.querySelector(s)?.getAttribute("aria-label") === "Pause",
    BTN, { timeout: 8000 }).catch(() => {});
  const waitEnded = () => page.waitForFunction(
    (s) => document.querySelector(s)?.getAttribute("aria-label") === "Play",
    BTN, { timeout: 60000 }).catch(() => {});

  // record the scene's playback duration so build_social.sh can trim exactly
  const total = await page.evaluate(() => {
    const t = document.querySelector(".scene-controls .time-display")?.textContent || "";
    const m = (t.split("/").pop() || "").trim().match(/(\d+):(\d+(?:\.\d+)?)/);
    return m ? Number(m[1]) * 60 + Number(m[2]) : null;
  });
  if (total) fs.writeFileSync(`${OUT}/scene_keep.txt`,
                              String((2 * total + 3.5).toFixed(1)));

  // pass 1: full playback with the orbit sweeps
  await clickPlay(); await waitPlaying();
  await sleep(1200);
  await drag(0.62, 0.30, 60, 52);    // slow sweep left  (~3.3 s)
  await sleep(800);
  await drag(0.30, 0.58, 52, 34);    // gentle sweep back (~2.9 s)
  await waitEnded();
  await sleep(600);
  // pass 2: restart from the beginning and play through untouched
  await clickPlay(); await waitPlaying();
  await waitEnded();
  await sleep(800);
};

// ---- record every scenario at both aspect ratios ---------------------------
// ONLY=gallery|video|scene re-records a single scenario while iterating.
const ONLY = process.env.ONLY;
const SCENARIOS = [
  ["gallery", gallerySetup, galleryAction],
  ["video",   videoSetup,   videoAction],
  ["scene",   sceneSetup,   sceneAction],
].filter(([n]) => !ONLY || n === ONLY);
const VIEWPORTS = [["169", 1600, 900], ["sq", 1080, 1080]];
for (const [tag, W, H] of VIEWPORTS) {
  for (const [name, setup, action] of SCENARIOS) {
    await record(`${name}-${tag}`, W, H, setup, action);
  }
}

await browser.close();
console.log("DONE");
