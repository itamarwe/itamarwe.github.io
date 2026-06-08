// Inject the GA4 (gtag.js) snippet into the embedded static apps' index.html
// at build time, using the same NEXT_PUBLIC_GA_ID the Next site uses, so
// /solar-system/ and /photo-geolocation/ report to the same GA4 property.
//
// These apps are plain static HTML served from public/ — they are NOT rendered
// by Next, so the <Analytics /> component in app/layout.tsx never touches them.
//
// Behaviour mirrors components/Analytics.tsx: when NEXT_PUBLIC_GA_ID is unset
// (e.g. local `npm run build` without the env var exported), this is a no-op,
// so no analytics is emitted and committed files aren't modified. On Vercel the
// var is a real environment variable, so the snippet is injected into the build.
import { readFileSync, writeFileSync, existsSync } from 'node:fs'

const gaId = process.env.NEXT_PUBLIC_GA_ID
if (!gaId) {
  console.log('[inject-ga] NEXT_PUBLIC_GA_ID not set — skipping analytics injection.')
  process.exit(0)
}

const MARKER = '<!-- ga4 (injected by scripts/inject-ga.mjs) -->'
const snippet = `${MARKER}
    <script async src="https://www.googletagmanager.com/gtag/js?id=${gaId}"></script>
    <script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','${gaId}');</script>`

const targets = [
  'public/solar-system/index.html',
  'public/photo-geolocation/index.html',
]

for (const file of targets) {
  if (!existsSync(file)) {
    console.log(`[inject-ga] ${file} not found — skipping.`)
    continue
  }
  let html = readFileSync(file, 'utf8')
  if (html.includes(MARKER)) {
    console.log(`[inject-ga] ${file} already has the tag — skipping.`)
    continue
  }
  if (!html.includes('</head>')) {
    console.warn(`[inject-ga] ${file} has no </head> — skipping.`)
    continue
  }
  html = html.replace('</head>', `    ${snippet}\n  </head>`)
  writeFileSync(file, html)
  console.log(`[inject-ga] injected GA4 (${gaId}) into ${file}`)
}
