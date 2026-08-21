import test from "node:test";
import assert from "node:assert/strict";
import { hasMarkdownVariant } from "../lib/markdown-paths.ts";

test("negotiable paths", () => {
  for (const p of [
    "/",
    "/about",
    "/about/",
    "/contact/",
    "/privacy/",
    "/blog/gaussian-splatting/",
    "/blog/gaussian-splatting",
    "/blog/",
  ]) {
    assert.equal(hasMarkdownVariant(p), true, p);
  }
});

test("non-negotiable paths", () => {
  for (const p of [
    "/fpv/",
    "/fpv/video/foo/",
    "/feed.xml",
    "/sitemap.xml",
    "/llms.txt",
    "/blog/a/b/",
    "/solar-system/",
    "/md/about/",
    "/aboutx",
  ]) {
    assert.equal(hasMarkdownVariant(p), false, p);
  }
});
