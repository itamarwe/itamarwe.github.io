// Browser-side logic for the "hello" MCP App.
//
// This runs inside the host's sandboxed iframe. It speaks the real MCP Apps
// SEP protocol (JSON-RPC over postMessage) via the official `App` client, which
// is what makes the difference between "Claude renders the card" and "the iframe
// collapses to nothing":
//   • `autoResize` reports the document height to the host, so the iframe is
//     actually given height (otherwise it stays ~0px and you see nothing).
//   • the host hands us the tool result + theme through the connect handshake.
//
// esbuild bundles this together with vendor/mcp-app-sdk.js into a single inline
// <script> (see build.mjs) so it works in a null-origin sandbox with no network.

import { App, applyDocumentTheme, applyHostStyleVariables } from "../vendor/mcp-app-sdk.js";

const nameEl = document.getElementById("name");

function applyName(result) {
  // We echo the greeted name in the tool's structuredContent.
  const name = result?.structuredContent?.name;
  if (name) nameEl.textContent = name;
}

function applyTheme(ctx) {
  if (!ctx) return;
  if (ctx.theme) applyDocumentTheme(ctx.theme); // sets data-theme on <html>
  if (ctx.styles?.variables) applyHostStyleVariables(ctx.styles.variables);
}

// 1. Create the app (autoResize keeps the iframe sized to our content).
const app = new App({ name: "Hello App", version: "0.1.0" }, { autoResize: true });

// 2. Register handlers BEFORE connecting so no notifications are missed.
app.ontoolresult = applyName;
app.onhostcontextchanged = applyTheme;
app.onerror = (e) => console.error("[hello-app]", e);

// 3. Connect, then paint the initial theme + any result already available.
app.connect().then(() => applyTheme(app.getHostContext()));
