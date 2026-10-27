# itamar-weiss.com — using this design system

This is a **styling-only** design system (no React components — `window.ItamarWeiss` is intentionally empty). Build your own markup and style it with the tokens and classes below. Everything ships through `styles.css`'s import closure; no provider, wrapper, or theme setup is needed.

**The system is always-dark.** Set page roots to `background: var(--background)` (pure black `#000000`) and `color: var(--foreground)`; there is no light theme. Body type is `var(--font-geist-sans)` at `var(--font-size-base)` (17px) / line-height `var(--line-height-base)` (1.65).

## Tokens (CSS custom properties, defined on `:root`)

| Token | Value | Use |
|---|---|---|
| `--background` | `#000000` | page canvas — always pure black |
| `--foreground` | `#ededed` | body text |
| `--heading` | `#ffffff` | headings (h1–h6 are already styled: weight 600, `-0.01em` tracking) |
| `--brand` | `#3291ff` | links, primary emphasis |
| `--brand-hover` | `#ffffff` | link hover |
| `--muted` | `#a1a1a1` | secondary text, captions, metadata |
| `--border` | `#333333` | hairlines, rules, card borders |
| `--code-bg` | `#111111` | code/panel background (panels may sit a hair lighter than black) |
| `--accent-cyan` `#3fc1ff` · `--accent-gold` `#ffd166` · `--accent-green` `#7CFC8A` · `--accent-red` `#ff5a5a` · `--accent-purple` `#b48cff` | | figure/diagram/chart accent palette — use these (in this order of preference) for data series, highlights, and illustrations |
| `--font-geist-sans` / `--font-geist-mono` / `--font-doto` | | font stacks (all three families ship in `fonts/`) |
| `--spacing-unit` | `30px` | base spacing rhythm (halves/multiples of it) |
| `--content-width` | `800px` | max text-column width |

`--font-doto` is a dot-matrix display font: use it **only** for the site-title/logo mark or a large display numeral — never body text.

## Class vocabulary (from the site's real stylesheet)

Bare elements are pre-styled: `a` (brand-blue, underlined), `blockquote` (muted italic, 4px `--border` left rule), `pre`/`code` (Geist Mono on `--code-bg` with a `--border` 6px-radius box), `h1`–`h6`. Layout classes: `.wrapper` (centered `--content-width` column with side padding), `.site-header` / `.site-title` / `.site-nav` / `.page-link` (top bar: 56px line, bottom hairline, Doto title), `.page-content` (main padded region), `.post-title` (42px, `-0.03em`), `.post-meta` (small muted), `.post-list` / `.post-link` (unbulleted index of 24px links). For anything beyond these, write your own CSS using the tokens above — don't invent new utility-class names.

## Idiomatic example

```html
<header class="site-header"><div class="wrapper">
  <a class="site-title" href="/">Itamar Weiss</a>
  <nav class="site-nav"><a class="page-link" href="/about/">About</a></nav>
</div></header>
<div class="page-content"><div class="wrapper">
  <h1 class="post-title">Slide or article title</h1>
  <p class="post-meta">August 2026 · drones</p>
  <p>Body copy with <a href="#">a brand-blue link</a>.</p>
  <div style="display:flex;gap:12px">
    <div style="background:var(--code-bg);border:1px solid var(--border);border-radius:6px;padding:16px">
      <span style="color:var(--accent-cyan);font-family:var(--font-geist-mono)">a stat or figure</span>
    </div>
  </div>
</div></div>
```

Read `styles.css` → `_ds_bundle.css` for the full stylesheet (tokens first, then the site's compiled CSS) before styling anything unusual.
