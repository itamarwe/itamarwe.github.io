# itamar-weiss.com

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
2. Add the production environment variable `NEXT_PUBLIC_GA_ID` (your `G-…` ID).
3. Add the custom domain `www.itamar-weiss.com` (and apex redirect) in
   **Project → Settings → Domains**. This replaces the old GitHub Pages `CNAME`.

Every push to `master` triggers a Vercel production deploy.

## URL scheme

- Posts now live at clean URLs: `/blog/<slug>/`
- Every old Jekyll URL (e.g. `/drones/2024/12/07/how-does-a-drone-fly.html`,
  including the comma-quirk paths) issues a permanent redirect to the new URL.
