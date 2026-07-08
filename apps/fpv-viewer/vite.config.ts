import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Built like the other embedded apps (see apps/photo-geolocation): relative
// asset URLs and output written straight into the site's public/ dir, served
// at /fpv via the rewrites in next.config.ts. All data (videos, thumbnails,
// scenes, and the videos.json manifest) is fetched from CloudFront at runtime,
// published by the dataset repo's `npm run publish-web`.
export default defineConfig(({ command }) => ({
  base: command === "build" ? "./" : "/",
  plugins: [react()],
  server: { port: 5185 },
  build: {
    outDir: "../../public/fpv",
    emptyOutDir: true,
  },
}));
