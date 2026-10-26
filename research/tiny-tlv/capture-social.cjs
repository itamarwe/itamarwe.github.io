/** Capture the actual shipped WebGL model; no synthetic scene or image generation.
 * The capture-only camera handle and card layout are injected into the local
 * response, leaving the public viewer and its controls unchanged.
 * Run against a local static or Next server. Outputs are relative to this file.
 */
const { createRequire } = require('node:module');
const { readFile, mkdir } = require('node:fs/promises');
const path = require('node:path');
const repo = path.resolve(__dirname, '../..');
const { chromium } = createRequire(path.join(repo, 'apps/photo-geolocation/package.json'))('playwright');
const origin = process.argv[2] || 'http://localhost:3018';
if (!['localhost', '127.0.0.1', '[::1]'].includes(new URL(origin).hostname)) {
  throw new Error('Capture against a local server, not the live website.');
}
(async () => {
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.CHROME_BIN ? { executablePath: process.env.CHROME_BIN } : {}),
    args: ['--use-gl=angle'],
  });
  try {
    const page = await browser.newPage({ viewport: { width: 1200, height: 630 }, reducedMotion: 'reduce' });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const html = await readFile(path.join(repo, 'public/tiny-tlv/index.html'), 'utf8');
    const hook = 'renderer.setAnimationLoop(() => {';
    if (!html.includes(hook)) throw new Error('Viewer capture hook changed.');
    await page.route(`${origin}/tiny-tlv/`, route => route.fulfill({
      contentType: 'text/html',
      body: html.replace(hook, 'window.__capture = { scene, camera, controls, renderer, home };\n' + hook),
    }));
    await page.goto(`${origin}/tiny-tlv/`);
    await page.locator('#loader').waitFor({ state: 'hidden', timeout: 60000 });
    await page.evaluate(() => document.fonts.ready);
    await page.addStyleTag({ content: `
      body { background: #000; }
      header.hud, footer.hud, .controls { display: none; }
      #share { position: fixed; inset: 0; pointer-events: none; color: #faf8f2; }
      #share .eyebrow { position:absolute; top: 54px; left: 48px; font: 500 13px var(--mono); letter-spacing: .18em; color: #3fc1ff; }
      #share h1 { position: absolute; top: 104px; left: 44px; font-size: 78px; line-height: .99; letter-spacing: -.04em; }
      #share p { position: absolute; top: 300px; left: 48px; font: 300 24px/1.4 var(--display); color: #a9a597; }
      #share .url { position: absolute; left: 48px; bottom: 40px; font: 400 16px var(--mono); color: #a9a597; }
      #share .credit { position: absolute; right: 24px; bottom: 18px; font: 300 10px var(--display); color: #8b95a5; }
      @media (min-height: 900px) {
        #share .eyebrow { top: 54px; }
        #share h1 { top: 95px; font-size: 92px; }
        #share h1 br { display: none; }
        #share p { top: 215px; }
        #share p br { display: none; }
        #share .url { bottom: 54px; font-size: 20px; }
      }
    ` });
    await page.evaluate(() => {
      const share = document.createElement('div');
      share.id = 'share';
      share.innerHTML = '<div class="eyebrow">EXPLORE IN 3D</div><h1>Tiny<br> Tel Aviv</h1><p>Shalom Meir Tower &amp;<br> the streets around it.</p><div class="url">itamarweiss.com/tiny-tlv</div><div class="credit">Data: © OpenStreetMap contributors · Tel Aviv-Yafo GIS · Photos: Wikimedia Commons</div>';
      document.body.append(share);
    });
    const out = path.join(repo, 'public/img/tiny-tlv');
    await mkdir(out, { recursive: true });
    for (const [name, width, height] of [['social.png', 1200, 630], ['social-square.png', 1080, 1080]]) {
      await page.setViewportSize({ width, height });
      await page.evaluate(({ width, height }) => {
        const { scene, camera, controls, renderer, home } = window.__capture;
        controls.autoRotate = false;
        scene.background.set('#000000');
        camera.position.copy(home.pos).sub(home.target).normalize().multiplyScalar(2.42).add(home.target);
        controls.target.copy(home.target);
        camera.clearViewOffset();
        camera.aspect = width / height;
        camera.zoom = height > 900 ? .42 : .55;
        camera.setViewOffset(width, height, height > 900 ? 0 : -210, height > 900 ? 20 : 90, width, height);
        camera.updateProjectionMatrix();
        controls.update();
        renderer.setPixelRatio(1);
        renderer.setSize(width, height);
        renderer.render(scene, camera);
      }, { width, height });
      await page.screenshot({ path: path.join(out, name) });
      console.log(`Captured ${name}: ${width} × ${height}`);
    }
    if (errors.length) throw new Error(errors.join('\n'));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
