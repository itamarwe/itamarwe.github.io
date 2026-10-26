/** Record the actual Tiny TLV website with a deterministic, seamless camera path.
 * Captures real browser frames (not a rebuilt scene); no server files are patched.
 * Frame-by-frame capture keeps 30 fps even when rendering is slower than real time.
 * Usage: CHROME_BIN=/path/to/chrome node research/tiny-tlv/capture-orbit.cjs [--linkedin] [--preview]
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
const linkedin = process.argv.includes('--linkedin');
const width = linkedin ? 1080 : 1920, height = 1080, fps = 30;
const duration = linkedin ? 13 : 36, frames = fps * duration;
const basename = linkedin ? 'tiny-tlv-linkedin-loop' : 'tiny-tlv-orbit';
const preview = process.argv.includes('--preview');
const out = path.join(repo, `public/img/tiny-tlv/${basename}.mp4`);
const scratch = path.join(__dirname, linkedin ? 'out/linkedin' : 'out/orbit');
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
    if (linkedin) await page.addStyleTag({ content: `
      header.hud { top: 56px; left: 64px; right: 64px; gap: 16px; }
      header.hud h1 { font-size: 72px; }
      .sub { font-size: 18px; letter-spacing: 0.03em; }
      .stats, .controls { display: none; }
      footer.hud { left: 64px; right: 64px; bottom: 36px; max-width: none; }
      .credits { font-size: 12px; }
      #capture-url { top: auto; bottom: 108px; left: 64px; right: auto; font-size: 28px; }
    ` });
    await page.evaluate(linkedin => {
      const { renderer, controls, camera } = window.__capture;
      camera.setViewOffset(innerWidth, innerHeight, 0, linkedin ? 0 : 70, innerWidth, innerHeight);
      if (linkedin) camera.fov = 34;
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
      // The reference's repeat cycle: 3 s angled, 2.5 s rise, 5 s overhead,
      // 2.5 s return. Quintic easing stops smoothly at both ends of each tilt.
      const smootherstep = x => x ** 3 * (x * (6 * x - 15) + 10);
      const topBlend = seconds => seconds < 3 ? 0
        : seconds < 5.5 ? smootherstep((seconds - 3) / 2.5)
        : seconds < 10.5 ? 1
        : 1 - smootherstep((seconds - 10.5) / 2.5);
      window.__orbitFrame = t => {
        const { camera, scene } = window.__capture;
        const zoom = Math.sin(Math.PI * t) ** 2;
        // LinkedIn keeps both distance and field of view fixed. The periodic
        // tilt reaches 85 degrees, avoiding the camera up-vector singularity.
        const distance = linkedin ? 6.5 : 4.1 + 2.4 * zoom;
        const tilt = linkedin ? topBlend(t * 13) : zoom;
        const elevation = (35 + (linkedin ? 50 : 6) * tilt) * Math.PI / 180;
        // A small periodic sideways drift settles to a fixed heading overhead.
        // This replaces the full spin, which competed with the reference's pause.
        const azimuth = -Math.PI / 4 + (linkedin
          ? 12 * Math.PI / 180 * Math.sin(2 * Math.PI * t) * (1 - tilt)
          : 6 * Math.PI * t);
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
    }, linkedin);
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
    if (linkedin && !preview) {
      await writeFile(path.join(repo, 'public/img/tiny-tlv/tiny-tlv-linkedin-thumbnail.png'), first);
    }
    if (preview) {
      for (const [i, t] of (linkedin ? [3/13, 4.25/13, 5.5/13, 10.5/13, 11.75/13] : [1/6, 1/3, 1/2, 2/3, 5/6]).entries()) {
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
        orbits: linkedin ? 0 : 3, fixedZoom: linkedin,
        ...(linkedin ? { cameraDistance: 6.5, fieldOfView: 34, elevationDegrees: [35, 85, 35],
          motion: { angledHoldSeconds: 3, riseSeconds: 2.5, overheadHoldSeconds: 5,
            returnSeconds: 2.5, easing: 'quintic smootherstep', yawAmplitudeDegrees: 12 },
          motionReference: 'https://mappalabs.com/?drape=alpine&stereo=off' } : {}),
        audio: false, loopEndpointIdentical: true,
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
