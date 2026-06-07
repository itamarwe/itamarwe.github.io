# itamarweiss.com

Personal blog of Itamar Weiss — **Next.js** (App Router) site deployed on **Vercel**.

Migrated from Jekyll/GitHub Pages. All legacy URLs are preserved via permanent
redirects, so nothing that pointed at the old site breaks.

## Tech stack

- [Next.js 15](https://nextjs.org/) (App Router, React 19, TypeScript)
- Markdown posts rendered at build time with `remark` / `rehype`
  (GFM, raw HTML, and `highlight.js` syntax highlighting)
- Sass for styling (ported from the original theme)
- Disqus comments, GA4 analytics, RSS, sitemap, and robots

## Project structure

```
app/
  layout.tsx            Root layout: <head> metadata, GA4, header, footer
  page.tsx              Home (post list)
  about/  portfolio/    Static pages
  blog/[slug]/          Blog posts (statically generated)
  feed.xml/route.ts     RSS feed (full content, latest 10)
  sitemap.ts            sitemap.xml
  robots.ts             robots.txt
content/
  posts/*.md            Blog posts (frontmatter + markdown)
  pages/*.md            About / Portfolio content
lib/                    Post loading, URL logic, markdown rendering, redirects
components/             Header, Footer, Disqus, Analytics
styles/globals.scss     Ported theme + dark mode + syntax highlighting
public/                 img/, solar-system/ (WebGL demo), favicon.ico
```

## Local development

```bash
npm install
npm run dev      # http://localhost:3000
npm run build    # production build
npm run start    # serve the production build
```

## Configuration

| What | Where |
| --- | --- |
| Site title / URL / socials | `lib/site.ts` |
| Google Analytics 4 ID | `NEXT_PUBLIC_GA_ID` env var (see `.env.example`) |
| Legacy URL redirects | generated in `lib/redirects.ts` from each post |

## Deploying to Vercel

1. Import the repo into Vercel (framework preset: **Next.js** — auto-detected).
2. Add the Google Analytics 4 environment variable (see below).
3. Add the custom domain `www.itamarweiss.com` as the **Primary** domain in
   **Project → Settings → Domains**, and keep the old `www.itamar-weiss.com`
   attached so it 301-redirects to the new domain (preserving SEO).

Every push to `master` triggers a Vercel production deploy.

## Google Analytics 4

The GA4 tag is injected from the `NEXT_PUBLIC_GA_ID` environment variable
(rendered by `components/Analytics.tsx`). When the variable is unset, no
analytics script is emitted, so local/dev builds stay clean.

To enable it in production:

1. In Google Analytics, copy your **Measurement ID** — it looks like
   `G-XXXXXXXXXX` (Admin → Data Streams → your web stream → Measurement ID).
   Note: this is **not** the old Universal Analytics number (`UA-…`/`41407229`).
2. In Vercel → **Project → Settings → Environment Variables**, add:
   - **Key:** `NEXT_PUBLIC_GA_ID`
   - **Value:** your `G-XXXXXXXXXX` ID
   - **Environments:** Production (and Preview, if you want analytics there too)
3. **Redeploy.** Because the value is a `NEXT_PUBLIC_*` variable, it is inlined
   at build time, so the tag only appears after a fresh deploy.

For local testing, copy `.env.example` to `.env.local` and set the value there.

## URL scheme

- Posts now live at clean URLs: `/blog/<slug>/`
- Every old Jekyll URL (e.g. `/drones/2024/12/07/how-does-a-drone-fly.html`,
  including the comma-quirk paths) issues a permanent redirect to the new URL.
