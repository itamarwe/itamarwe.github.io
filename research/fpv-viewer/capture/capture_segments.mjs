import pw from "playwright";
import fs from "node:fs";
const { chromium } = pw;

const BASE = "http://localhost:5185";
const SLUG = "2026-05-26_anti_drone_platform_barashit.mp4";
const OUT = "./out";
fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT, { recursive: true });
const W = 1280, H = 800;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await chromium.launch({
  headless: true,
  args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
         "--ignore-gpu-blocklist", "--enable-webgl", "--autoplay-policy=no-user-gesture-required"],
});

async function segment(name, setup, action) {
  const dir = `${OUT}/${name}`;
  fs.mkdirSync(dir, { recursive: true });
  const ctx = await browser.newContext({
    viewport: { width: W, height: H }, deviceScaleFactor: 1,
    recordVideo: { dir, size: { width: W, height: H } },
  });
  const page = await ctx.newPage();
  page.on("console", (m) => { if (m.type() === "error") console.log(`[${name}] ERR`, m.text()); });
  await page.addStyleTag({ content: `::-webkit-scrollbar{width:0;height:0}html{scrollbar-width:none}` }).catch(()=>{});
  await setup(page);
  await action(page);
  await ctx.close();
  const webm = fs.readdirSync(dir).find((f) => f.endsWith(".webm"));
  console.log(name, "->", webm);
  return `${dir}/${webm}`;
}

// ---- Gallery ----
await segment("gallery",
  async (page) => {
    await page.goto(`${BASE}/#/`, { waitUntil: "domcontentloaded" });
    await page.addStyleTag({ content: `::-webkit-scrollbar{width:0;height:0}html{scrollbar-width:none}` }).catch(()=>{});
    await page.waitForSelector(".video-card", { timeout: 20000 });
    // wait until thumbnails have actually decoded (no blur)
    await page.waitForFunction(() => {
      const imgs = [...document.querySelectorAll(".video-card img")].slice(0, 9);
      return imgs.length >= 6 && imgs.every((i) => i.complete && i.naturalWidth > 0);
    }, { timeout: 25000 }).catch(() => {});
    // filter to 3D scenes
    const btn = page.getByRole("button", { name: /3D scenes/i });
    if (await btn.count()) await btn.first().click().catch(() => {});
    await sleep(900);
  },
  async (page) => {
    await sleep(700);
    // smooth scroll down then settle
    await page.evaluate(async () => {
      const dur = 2200, start = performance.now(), max = 620;
      await new Promise((res) => {
        const step = (t) => { const k = Math.min((t - start) / dur, 1);
          window.scrollTo(0, max * (0.5 - 0.5 * Math.cos(k * Math.PI)));
          k < 1 ? requestAnimationFrame(step) : res(); };
        requestAnimationFrame(step);
      });
    });
    await sleep(700);
  });

// ---- Video interface ----
await segment("video",
  async (page) => {
    await page.evaluate((s) => { location.hash = `#/video/${s}`; window.scrollTo(0,0); }, SLUG);
    await page.goto(`${BASE}/#/video/${SLUG}`, { waitUntil: "domcontentloaded" });
    await page.addStyleTag({ content: `::-webkit-scrollbar{width:0;height:0}html{scrollbar-width:none}` }).catch(()=>{});
    await page.waitForSelector("video", { timeout: 20000 });
    await page.waitForFunction(() => {
      const v = document.querySelector("video");
      return v && v.readyState >= 2;
    }, { timeout: 20000 }).catch(() => {});
    await page.evaluate(async () => {
      const v = document.querySelector("video");
      if (v) { v.muted = true; v.currentTime = 6; try { await v.play(); } catch (e) {} }
    });
  },
  async () => { await sleep(4600); });

// ---- Scene interface ----
await segment("scene",
  async (page) => {
    await page.goto(`${BASE}/#/scene/${SLUG}`, { waitUntil: "domcontentloaded" });
    await page.addStyleTag({ content: `::-webkit-scrollbar{width:0;height:0}html{scrollbar-width:none}` }).catch(()=>{});
    await page.waitForFunction(() => {
      const st = document.querySelector(".scene-status");
      const cv = document.querySelector(".canvas-holder canvas");
      return cv && (!st || !st.textContent);
    }, { timeout: 45000 }).catch(() => {});
    await sleep(1000);
  },
  async (page) => {
    // clean still (before playback) for the social card
    const stage0 = await page.$(".scene-stage");
    if (stage0) await stage0.screenshot({ path: `${OUT}/scene_still.png` });
    await page.evaluate(() => document.querySelector(".play-btn")?.click());
    await sleep(2600); // path draws + frame panel updates
    const stage = await page.$(".scene-stage");
    const box = stage ? await stage.boundingBox() : { x: 120, y: 210, width: 900, height: 460 };
    const cy = box.y + box.height * 0.52;
    await page.mouse.move(box.x + box.width * 0.6, cy);
    await page.mouse.down();
    for (let i = 0; i <= 28; i++) {
      await page.mouse.move(box.x + box.width * (0.6 - i * 0.011), cy - Math.sin((i / 28) * Math.PI) * 46);
      await sleep(42);
    }
    await page.mouse.up();
    await sleep(1200);
  });

await browser.close();
console.log("DONE");
