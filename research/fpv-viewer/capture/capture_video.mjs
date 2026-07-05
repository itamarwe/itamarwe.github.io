import pw from "playwright";
import fs from "node:fs";
const { chromium } = pw;
const BASE = "http://localhost:5185";
const SLUG = "2026-05-26_anti_drone_platform_barashit.mp4";
const OUT = "./out/video";
fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT, { recursive: true });
const W = 1280, H = 800;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await chromium.launch({
  headless: true,
  args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
         "--ignore-gpu-blocklist", "--enable-webgl", "--autoplay-policy=no-user-gesture-required"],
});
const ctx = await browser.newContext({
  viewport: { width: W, height: H }, deviceScaleFactor: 1,
  recordVideo: { dir: OUT, size: { width: W, height: H } },
});
const page = await ctx.newPage();
await page.goto(`${BASE}/#/video/${SLUG}`, { waitUntil: "domcontentloaded" });
await page.addStyleTag({ content: `::-webkit-scrollbar{width:0;height:0}html{scrollbar-width:none}` }).catch(()=>{});
await page.waitForSelector("video", { timeout: 20000 });
await page.waitForFunction(() => { const v = document.querySelector("video"); return v && v.readyState >= 2; }, { timeout: 20000 }).catch(()=>{});
await page.waitForSelector(".timeline", { timeout: 10000 }).catch(()=>{});
await page.evaluate(async () => {
  const v = document.querySelector("video");
  if (v) { v.muted = true; v.currentTime = 6; try { await v.play(); } catch (e) {} }
});
// action window (trimmed to the last ~5.4s):
await sleep(1600);                       // show the clip playing
await page.evaluate(() => {              // reveal the flight-annotation ribbon
  document.querySelector(".timeline")?.scrollIntoView({ behavior: "smooth", block: "center" });
});
await sleep(3600);                        // hold on annotations + moving playhead
await ctx.close();
await browser.close();
console.log("video ->", fs.readdirSync(OUT).find((f) => f.endsWith(".webm")));
