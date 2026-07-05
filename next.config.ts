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
  async rewrites() {
    return [
      { source: "/solar-system", destination: "/solar-system/index.html" },
      { source: "/solar-system/", destination: "/solar-system/index.html" },
      { source: "/photo-geolocation", destination: "/photo-geolocation/index.html" },
      { source: "/photo-geolocation/", destination: "/photo-geolocation/index.html" },
      { source: "/fpv", destination: "/fpv/index.html" },
      { source: "/fpv/", destination: "/fpv/index.html" },
    ];
  },

  // Permanent (301/308) redirects from every legacy Jekyll URL to the new
  // clean URL, so existing links and search-engine results keep working.
  // The Portfolio page was merged into About, so /portfolio/ now redirects there.
  async redirects() {
    return [
      ...legacyRedirects,
      { source: "/portfolio", destination: "/about/", permanent: true },
    ];
  },
};

export default nextConfig;
