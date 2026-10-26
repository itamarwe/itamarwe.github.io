/** Record the actual Tiny TLV website with a deterministic, seamless camera path.
 * Captures real browser frames (not a rebuilt scene); no server files are patched.
 * Frame-by-frame capture keeps 30 fps even when rendering is slower than real time.
 * Usage: CHROME_BIN=/path/to/chrome node research/tiny-tlv/capture-orbit.cjs [--preview]
 */
const { createRequire } = require('node:module');
const { mkdir, writeFile } = require('node:fs/promises');
const { createHash } = require('node:crypto');
const { spawn } = require('node:child_process');
const { once } = require('node:events');
const path = require('node:path');
const repo = path.resolve(__dirname, '../..');
const { chromium } = createRequire(path.join(repo, 'apps/photo-geolocation/package.json'))('playwright');
const sourceUrl = 'https://www.itamarweiss.com/tiny-tlv/';
const width = 1920, height = 1080, fps = 30, duration = 36, frames = fps * duration;
const preview = process.argv.includes('--preview');
const out = path.join(repo, 'public/img/tiny-tlv/tiny-tlv-orbit.mp4');
const scratch = path.join(__dirname, 'out/orbit');
const sha = buffer => createHash('sha256').update(buffer).digest('hex');

(async () => {
  await mkdir(scratch, { recursive: true });
  const response = await fetch(sourceUrl);
  if (!response.ok) throw new Error(`Website returned ${response.status}`);
  const html = await response.text();
  const hook = 'renderer.setAnimationLoop(() => {';
  if (!html.includes(hook)) throw new Error('Live viewer capture hook changed.');
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.CHROME_BIN ? { executablePath: process.env.CHROME_BIN } : {}),
    args: ['--use-gl=angle'],
  });
  let encoder;
  try {
    const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1, reducedMotion: 'reduce' });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route(sourceUrl, route => route.fulfill({
      contentType: 'text/html',
      body: html.replace(hook, 'window.__capture = { scene, camera, controls, renderer };\n' + hook),
    }));
    await page.goto(sourceUrl);
    await page.locator('#loader').waitFor({ state: 'hidden', timeout: 60000 });
    await page.evaluate(() => document.fonts.ready);
    // Keep the website's own title, data, credits, and controls visible. Add its
    // address for viewers seeing the clip outside a browser; hide the idle hint.
    await page.addStyleTag({ content: `
      header.hud { top: 30px; left: 32px; }
      header.hud h1 { font-size: 64px; }
      .sub { font-size: 13px; }
      footer.hud { left: 32px; bottom: 30px; max-width: 490px; }
      .controls { right: 32px; bottom: 30px; }
      .hint { display: none; }
      #capture-url { position: fixed; top: 37px; right: 32px; font: 400 20px var(--mono); color: var(--paper); }
    ` });
    await page.evaluate(() => {
      const { renderer, controls, camera } = window.__capture;
      camera.setViewOffset(innerWidth, innerHeight, 0, 70, innerWidth, innerHeight);
      camera.updateProjectionMatrix();
      renderer.setAnimationLoop(null);
      controls.autoRotate = false;
      controls.enableDamping = false;
      controls.enabled = false;
      // The city and light are static; shadows do not change as the camera orbits.
      renderer.shadowMap.autoUpdate = false;
      renderer.shadowMap.needsUpdate = true;
      const address = document.createElement('div');
      address.id = 'capture-url';
      address.textContent = 'itamarweiss.com/tiny-tlv';
      document.body.append(address);
      document.getElementById('spin').setAttribute('aria-pressed', 'true');
      window.__orbitFrame = t => {
        const { camera, scene } = window.__capture;
        const zoom = Math.sin(Math.PI * t) ** 2;
        const distance = 4.1 + 2.4 * zoom;
        const elevation = (35 + 6 * zoom) * Math.PI / 180;
        const azimuth = -Math.PI / 4 + 6 * Math.PI * t;
        camera.position.set(
          distance * Math.cos(elevation) * Math.sin(azimuth),
          0.16 + distance * Math.sin(elevation),
          distance * Math.cos(elevation) * Math.cos(azimuth),
        );
        camera.lookAt(0, 0.16, 0);
        camera.updateMatrixWorld();
        renderer.render(scene, camera);
        return camera.position.toArray();
      };
    });
    const render = async t => {
      await page.evaluate(t => window.__orbitFrame(t), t);
      return page.screenshot({ type: 'png' });
    };
    const first = await render(0);
    const endpoint = await render(1);
    // The virtual endpoint is checked but not encoded, so playback does not pause
    // on a duplicate frame. The final-to-first step is one normal 1/30 s interval.
    if (sha(first) !== sha(endpoint)) throw new Error('Loop endpoint does not match the opening frame.');
    await writeFile(path.join(scratch, 'start.png'), first);
    await writeFile(path.join(scratch, 'endpoint.png'), endpoint);
    if (preview) {
      for (const [i, t] of [1/6, 1/3, 1/2, 2/3, 5/6].entries()) {
        await writeFile(path.join(scratch, `preview-${i + 1}.png`), await render(t));
      }
      console.log('Preview frames captured; loop endpoint is pixel-identical.');
    } else {
      encoder = spawn('ffmpeg', ['-hide_banner', '-loglevel', 'warning', '-y',
        '-f', 'image2pipe', '-vcodec', 'png', '-framerate', String(fps), '-i', 'pipe:0',
        '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
        '-maxrate', '8M', '-bufsize', '16M', '-pix_fmt', 'yuv420p',
        '-profile:v', 'high', '-level:v', '4.1', '-g', '60', '-movflags', '+faststart', out],
        { stdio: ['pipe', 'inherit', 'inherit'] });
      const finished = once(encoder, 'close');
      encoder.stdin.on('error', error => { errors.push(error.message); });
      for (let i = 0; i < frames; i++) {
        if (encoder.exitCode !== null) throw new Error('Video encoder exited early.');
        const frame = await render(i / frames);
        if (!encoder.stdin.write(frame)) await once(encoder.stdin, 'drain');
        if (i % 90 === 0) console.log(`Captured ${i}/${frames} frames (${(i / fps).toFixed(0)} s of ${duration} s)`);
        if (i === frames - 1) await writeFile(path.join(scratch, 'last.png'), frame);
      }
      encoder.stdin.end();
      const [code] = await finished;
      if (code !== 0) throw new Error(`ffmpeg exited with code ${code}`);
      await writeFile(path.join(scratch, 'capture.json'), JSON.stringify({
        sourceUrl, sourceHtmlSha256: sha(html), width, height, fps, duration, frames,
        orbits: 3, audio: false, loopEndpointIdentical: true,
        sourceTriangles: await page.locator('#s-tri').textContent(),
      }, null, 2) + '\n');
      console.log(`Created ${out}`);
    }
    if (errors.length) throw new Error(errors.join('\n'));
  } finally {
    if (encoder && encoder.exitCode === null) encoder.kill();
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
