# `/mcp` "hello" MCP App — widget build

Builds the self-contained HTML widget that the MCP server at
[`app/mcp/route.ts`](../../app/mcp/route.ts) serves as a UI resource. The server
itself (tools, resource registration, transport) is plain `mcp-handler` and
needs nothing here; this directory only produces the **browser-side app** that
Claude renders in the chat.

## Why a build step

The widget runs in the host's sandboxed, null-origin iframe, so it must be a
single HTML file with everything inlined — no external scripts. To speak the
real **MCP Apps SEP** protocol (the JSON-RPC-over-`postMessage` handshake that
lets the host size the iframe and pass theme + tool results) it uses the
official client from
[`@modelcontextprotocol/ext-apps`](https://github.com/modelcontextprotocol/ext-apps).

That package can't be a site dependency: its install rebuilds from source and
fails on Vercel, taking the whole `npm install` down with it. So we vendor its
prebuilt browser bundle (`vendor/mcp-app-sdk.js`, from `ext-apps` 1.7.4's
`app-with-deps.js`) and bundle it here, **locally**, leaving the site's runtime
deps untouched.

## Files

- `vendor/mcp-app-sdk.js` — vendored prebuilt MCP Apps SDK browser bundle.
- `src/view.js` — the app logic: create `App`, register handlers, `connect()`.
- `src/shell.html` — HTML + theme-aware CSS shell, with an `<!--APP-SCRIPT-->`
  placeholder.
- `build.mjs` — esbuild-bundles `src/view.js` + the SDK into one inline
  `<script>`, splices it into the shell, and writes the generated
  `app/mcp/widget.ts` (a string constant the route imports).

## Regenerate

```sh
cd research/mcp-app
npm install   # esbuild only; local, not part of the site build
npm run build # writes ../../app/mcp/widget.ts
```

`app/mcp/widget.ts` is generated and committed (Vercel serves it at runtime
without this build). Edit `src/` here, never `widget.ts` directly.
