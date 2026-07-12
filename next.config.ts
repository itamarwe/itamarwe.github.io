import type { NextConfig } from "next";
import { legacyRedirects } from "./lib/redirects";

const nextConfig: NextConfig = {
  // Jekyll/GitHub Pages served pages with trailing slashes (e.g. /about/).
  // Keep that behaviour so canonical URLs stay consistent.
  trailingSlash: true,

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
  async redirects() {
    return [
      ...legacyRedirects,
      { source: "/portfolio", destination: "/about/", permanent: true },
      {
        source: "/fpv/video/2026-05-26_anti_drone_platform_barashit",
        destination: "/fpv/video/2026-05-26_anti_drone_platform_biranit/",
        permanent: true,
      },
      {
        source: "/fpv/scene/2026-05-26_anti_drone_platform_barashit",
        destination: "/fpv/scene/2026-05-26_anti_drone_platform_biranit/",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
