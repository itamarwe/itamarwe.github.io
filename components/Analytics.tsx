import { GoogleAnalytics } from "@next/third-parties/google";

/**
 * Google Analytics 4. The Measurement ID is read from the NEXT_PUBLIC_GA_ID
 * environment variable (set it in Vercel → Project → Settings → Environment
 * Variables, e.g. "G-XXXXXXXXXX"). When unset, no analytics script is emitted.
 *
 * This replaces the site's original Universal Analytics (UA-41407229-1) tag,
 * which Google shut down in July 2023.
 */
export default function Analytics() {
  const gaId = process.env.NEXT_PUBLIC_GA_ID;
  if (!gaId) return null;
  return <GoogleAnalytics gaId={gaId} />;
}
