import type { NextConfig } from "next";
import { legacyRedirects } from "./lib/redirects";

const nextConfig: NextConfig = {
  // Jekyll/GitHub Pages served pages with trailing slashes (e.g. /about/).
  // Keep that behaviour so canonical URLs stay consistent.
  trailingSlash: true,

  // The Sun–Earth WebGL demo is a pre-built static app living in
  // public/solar-system/. Serve its index.html at the directory URL.
  async rewrites() {
    return [
      { source: "/solar-system", destination: "/solar-system/index.html" },
      { source: "/solar-system/", destination: "/solar-system/index.html" },
    ];
  },

  // Permanent (301/308) redirects from every legacy Jekyll URL to the new
  // clean URL, so existing links and search-engine results keep working.
  async redirects() {
    return legacyRedirects;
  },
};

export default nextConfig;
