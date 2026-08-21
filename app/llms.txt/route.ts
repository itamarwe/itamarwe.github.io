import { llmsTxt } from "@/lib/agent-content";

/** /llms.txt (llmstxt.org): a markdown index of the site for AI agents. */
export const dynamic = "force-static";

export function GET() {
  return new Response(llmsTxt(), {
    headers: { "content-type": "text/plain; charset=utf-8" },
  });
}
