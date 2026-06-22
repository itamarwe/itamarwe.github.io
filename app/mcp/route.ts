// A minimal remote MCP server, served at /mcp.
//
// It exposes one "MCP App" — a tool whose result Claude renders as an
// interactive HTML card inline in the chat, rather than as plain text. The
// pieces, per the MCP Apps SEP:
//
//   • a UI resource (the HTML, at a `ui://` URI, mime `text/html;profile=mcp-app`)
//   • a tool that points at that resource via `_meta["ui/resourceUri"]`
//
// When the tool runs, the host fetches the resource and renders it, handing the
// tool's output to the iframe as render data. See ./widget.ts for the HTML.
//
// Transport is Streamable HTTP via `mcp-handler` (Vercel's Next.js adapter).

import { createMcpHandler } from "mcp-handler";
import { z } from "zod";
import { HELLO_WIDGET_HTML } from "./widget";

// MCP Apps SEP constants (kept inline so we don't depend on @mcp-ui/* packages).
const RESOURCE_URI_META_KEY = "ui/resourceUri";
const RESOURCE_MIME_TYPE = "text/html;profile=mcp-app";
const HELLO_APP_URI = "ui://hello/app.html";

const handler = createMcpHandler(
  (server) => {
    // The UI resource: the HTML document the host renders in an iframe.
    server.registerResource(
      "hello-app",
      HELLO_APP_URI,
      {
        title: "Hello App",
        description: "An interactive hello card.",
        mimeType: RESOURCE_MIME_TYPE,
      },
      async (uri) => ({
        contents: [
          {
            uri: uri.href,
            mimeType: RESOURCE_MIME_TYPE,
            text: HELLO_WIDGET_HTML,
          },
        ],
      }),
    );

    // The tool: returns a name, and tells the host to render it with the app.
    server.registerTool(
      "hello_app",
      {
        title: "Hello App",
        description:
          "Show an interactive hello card. Use this when the user wants to " +
          "see the example MCP app or be greeted by name.",
        inputSchema: { name: z.string().optional().describe("Who to greet.") },
        _meta: { [RESOURCE_URI_META_KEY]: HELLO_APP_URI },
      },
      async ({ name }) => {
        const who = name?.trim() || "there";
        return {
          content: [{ type: "text", text: `Rendered a hello card for ${who}.` }],
          structuredContent: { name: who },
          _meta: { [RESOURCE_URI_META_KEY]: HELLO_APP_URI },
        };
      },
    );
  },
  {
    serverInfo: { name: "itamar-weiss-mcp", version: "0.1.0" },
  },
  {
    // The site uses `trailingSlash: true`, so requests land on /mcp/.
    streamableHttpEndpoint: "/mcp/",
    // No Redis here; we don't need the legacy SSE transport.
    disableSse: true,
    verboseLogs: false,
  },
);

export { handler as GET, handler as POST, handler as DELETE };
