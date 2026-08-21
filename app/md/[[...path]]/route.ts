import { markdownForPath } from "@/lib/agent-content";
import { site } from "@/lib/site";

/**
 * Markdown mirror of the site's pages, per acceptmarkdown.com. The middleware
 * rewrites any negotiable path requested with `Accept: text/markdown` here,
 * so the canonical URLs themselves answer in markdown; hitting /md/... paths
 * directly works too. Unknown paths get the 404 recovery body with a real
 * 404 status.
 */
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ path?: string[] }> },
) {
  const { path = [] } = await params;
  const pathname = `/${path.join("/")}`;
  const { markdown, status } = markdownForPath(pathname);

  const headers = new Headers({
    "content-type": "text/markdown; charset=utf-8",
    // The same URL serves HTML or markdown depending on Accept — without
    // Vary a CDN could hand the cached HTML variant to a markdown client.
    vary: "Accept",
  });
  if (status === 200) {
    const canonical =
      pathname === "/" ? `${site.url}/` : `${site.url}${pathname.replace(/\/?$/, "/")}`;
    headers.set("link", `<${canonical}>; rel="canonical"`);
  }

  return new Response(markdown, { status, headers });
}
