import test from "node:test";
import assert from "node:assert/strict";
import {
  homeMarkdown,
  pageMarkdown,
  postMarkdown,
  notFoundMarkdown,
  markdownForPath,
  llmsTxt,
  MARKDOWN_PAGES,
} from "../lib/agent-content.ts";
import { getAllPosts } from "../lib/posts.ts";
import { site } from "../lib/site.ts";

test("home markdown has an H1, the intro, and every post", () => {
  const md = homeMarkdown();
  assert.match(md, /^# Itamar Weiss — Hands-on AI & Data Consultant\n/);
  assert.ok(md.length > 500, "homepage markdown must exceed 500 chars");
  for (const post of getAllPosts()) {
    assert.ok(md.includes(`[${post.title}](${site.url}${post.url})`), post.slug);
  }
});

test("every standalone page has a markdown variant with H1", () => {
  for (const segment of Object.keys(MARKDOWN_PAGES)) {
    const md = pageMarkdown(segment);
    assert.ok(md, segment);
    assert.match(md!, /^# /);
  }
  assert.equal(pageMarkdown("nope"), undefined);
});

test("post markdown carries title, canonical URL, and body", () => {
  const post = getAllPosts()[0];
  const md = postMarkdown(post.slug)!;
  assert.match(md, new RegExp(`^# ${post.title.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\n`));
  assert.ok(md.includes(`${site.url}${post.url}`));
  assert.ok(md.includes(post.body.trim().slice(0, 80)));
  assert.equal(postMarkdown("no-such-post"), undefined);
});

test("markdownForPath resolves all route shapes", () => {
  assert.equal(markdownForPath("/").status, 200);
  assert.equal(markdownForPath("/about/").status, 200);
  assert.equal(markdownForPath("/contact/").status, 200);
  assert.equal(markdownForPath("/privacy/").status, 200);
  const post = getAllPosts()[0];
  assert.equal(markdownForPath(`/blog/${post.slug}/`).status, 200);
  assert.equal(markdownForPath("/blog/does-not-exist/").status, 404);
  assert.equal(markdownForPath("/nope/").status, 404);
});

test("404 markdown points agents at recovery URLs and sanitizes the path", () => {
  const md = notFoundMarkdown("/we`ird\npath/");
  assert.ok(md.includes(`${site.url}/llms.txt`));
  assert.ok(md.includes(`${site.url}/sitemap.xml`));
  assert.ok(md.includes(`${site.url}/`));
  assert.ok(!md.includes("we`ird"), "backticks must be stripped from echoed path");
  assert.ok(md.includes("weird"), "sanitized path is still shown");
  const long = notFoundMarkdown("/" + "a".repeat(500));
  assert.ok(!long.includes("a".repeat(201)), "echoed path is length-capped");
});

test("llms.txt follows the llmstxt.org shape", () => {
  const txt = llmsTxt();
  const lines = txt.split("\n");
  assert.match(lines[0], /^# Itamar Weiss$/, "starts with an H1");
  assert.match(lines[2], /^> /, "H1 is followed by a blockquote summary");
  assert.ok(txt.includes("\n## When to use this site\n"), "when-to-use section");
  assert.ok(txt.includes("\n## Blog posts\n"));
  assert.ok(txt.includes("\n## Optional\n"));
  // No H3+ headings and no absolute-URL typos: every listed link is on-site
  // or a mailto.
  assert.ok(!/^###/m.test(txt));
  for (const m of txt.matchAll(/\]\((https?:\/\/[^)]+)\)/g)) {
    assert.ok(m[1].startsWith(site.url), `unexpected external link: ${m[1]}`);
  }
});

test("llms.txt lists every post with a resolvable URL", () => {
  const txt = llmsTxt();
  for (const post of getAllPosts()) {
    assert.ok(txt.includes(`(${site.url}${post.url})`), post.slug);
  }
});
