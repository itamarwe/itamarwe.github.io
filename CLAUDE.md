# itamarwe.github.io

Jekyll site published via GitHub Pages.

## Always verify links before adding them

This is a static site, so a typo in an internal link is a dead link in production. Before adding any link in a markdown file:

- **External links**: confirm the URL resolves (WebFetch or WebSearch).
- **Internal links**: confirm the target file exists and the URL matches Jekyll's actual generated path. The default permalink is `/:categories/:year/:month/:day/:title.html`, so the URL depends on the post's `categories:` frontmatter. Cross-check against an existing post's link to confirm the path format.
- **Watch the `categories:` field**: writing `categories: ai, code` as a comma-separated string does **not** produce `/ai/code/...` — Jekyll needs a YAML list (`categories: [ai, code]` or block style) or space-separated values.

## Pull request workflow

**Always branch and PR — never push directly to `master`.**

For every change, no matter how small:

1. **Create a new branch** from `master`
2. **Make commits** to that branch
3. **Open a pull request** — do not merge yourself; leave it for the user to review and merge

Once a PR is merged, that branch is closed. Do not push further commits to it — create a new branch for the next set of changes.
