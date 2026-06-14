// The HTML "app" that Claude renders inline when the `hello_app` tool runs.
//
// This is a self-contained MCP App (per the MCP Apps SEP): a single HTML
// document served as a `text/html;profile=mcp-app` resource. The host (Claude)
// drops it into a sandboxed iframe and hands it the tool's output as "render
// data" over a postMessage bridge. We keep it dependency-free so it renders
// anywhere.
//
// Render-data flow (the minimal slice of the SEP we use here):
//   1. The iframe tells the host it is ready.
//   2. The host replies with the tool result (our `{ name }`).
//   3. We paint the greeting. If no data ever arrives we fall back gracefully,
//      so the app still looks right when opened outside a host.

export const HELLO_WIDGET_HTML = /* html */ `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  html, body { margin: 0; }
  body {
    font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    background: #0e1116;
    color: #ededed;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 220px;
    padding: 24px;
  }
  .card {
    width: 100%;
    max-width: 420px;
    background: radial-gradient(120% 120% at 0% 0%, #161b22 0%, #0e1116 70%);
    border: 1px solid #232a35;
    border-radius: 16px;
    padding: 28px 28px 24px;
    box-shadow: 0 18px 40px rgba(0, 0, 0, 0.45);
  }
  .eyebrow {
    font-size: 12px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #8b95a5;
    margin: 0 0 10px;
  }
  h1 {
    font-size: 26px;
    line-height: 1.2;
    margin: 0 0 8px;
    font-weight: 650;
  }
  h1 .name { color: #3fc1ff; }
  p.sub { margin: 0; color: #8b95a5; font-size: 14px; }
  .wave {
    display: inline-block;
    animation: wave 1.8s ease-in-out infinite;
    transform-origin: 70% 70%;
  }
  @keyframes wave {
    0%, 60%, 100% { transform: rotate(0deg); }
    10% { transform: rotate(16deg); }
    20% { transform: rotate(-8deg); }
    30% { transform: rotate(16deg); }
    40% { transform: rotate(-4deg); }
    50% { transform: rotate(10deg); }
  }
</style>
</head>
<body>
  <div class="card">
    <p class="eyebrow">MCP App</p>
    <h1>Hello, <span class="name" id="name">there</span> <span class="wave">👋</span></h1>
    <p class="sub">This card is a live MCP App served from <code>/mcp</code>.</p>
  </div>

  <script>
    // Ask the host for the render data, then paint whatever name it gives us.
    function applyRenderData(data) {
      var name = data && (data.name || (data.toolOutput && data.toolOutput.name));
      if (name) document.getElementById("name").textContent = name;
    }

    window.addEventListener("message", function (event) {
      var msg = event.data || {};
      if (msg.type === "ui-lifecycle-iframe-render-data") {
        applyRenderData(msg.payload && msg.payload.renderData);
      }
    });

    // Announce readiness so the host knows it can send render data.
    try {
      window.parent.postMessage({ type: "ui-lifecycle-iframe-ready" }, "*");
    } catch (e) {}
  </script>
</body>
</html>`;
