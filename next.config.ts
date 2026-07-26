import type { NextConfig } from "next";
import { legacyRedirects } from "./lib/redirects";

const nextConfig: NextConfig = {
  // Jekyll/GitHub Pages served pages with trailing slashes (e.g. /about/).
  // Keep that behaviour so canonical URLs stay consistent.
  trailingSlash: true,

  // `lib/posts.ts` reads content/posts/*.md with fs.readdirSync at request
  // time, but Next's build tracer can't see through a runtime readdir, so the
  // markdown never lands in the serverless bundle. Routes that are fully
  // prerendered don't care; /sitemap.xml does, because fetching the FPV
  // manifest gives it a 5-minute revalidate and it re-runs in the Lambda
  // (ENOENT scandir '/var/task/content/posts'). Ship the content directory
  // with every function so any route can read it at runtime.
  outputFileTracingIncludes: {
    "/**": ["./content/**/*"],
  },

  // Embedded static apps living under public/<name>/ are served at their
  // directory URL. The Sun–Earth WebGL demo (public/solar-system/) is
  // pre-built and committed; the photo-geolocation tool (public/photo-
  // geolocation/) is built from apps/photo-geolocation/ during the site build.
  // The FPV viewer (/fpv) is now a native Next route group (app/fpv/), not a
  // static embed, so it needs no rewrite.
  async rewrites() {
    return [
      { source: "/solar-system", destination: "/solar-system/index.html" },
      { source: "/solar-system/", destination: "/solar-system/index.html" },
      {
        source: "/photo-geolocation",
        destination: "/photo-geolocation/index.html",
      },
      {
        source: "/photo-geolocation/",
        destination: "/photo-geolocation/index.html",
      },
    ];
  },

  // Permanent (301/308) redirects from every legacy Jekyll URL to the new
  // clean URL, so existing links and search-engine results keep working.
  // The Portfolio page was merged into About, so /portfolio/ now redirects there.
  //
  // Renamed FPV slugs are deliberately absent: they are served by
  // resolveLegacySlug from the dataset's own data/redirects.json, so a rename
  // takes effect on the next publish without redeploying this site. Hardcoding
  // them here too meant every rename needed a matching entry in two places, and
  // a forgotten one is a dead URL.
  async redirects() {
    return [
      ...legacyRedirects,
      { source: "/portfolio", destination: "/about/", permanent: true },
    ];
  },
};

export default nextConfig;
