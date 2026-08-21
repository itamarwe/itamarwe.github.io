import test from "node:test";
import assert from "node:assert/strict";
import { parseAccept, prefersMarkdown } from "../lib/accept.ts";

test("explicit text/markdown gets markdown", () => {
  assert.equal(prefersMarkdown("text/markdown"), true);
});

test("markdown listed alongside html (equal q) gets markdown", () => {
  assert.equal(prefersMarkdown("text/html, text/markdown"), true);
  assert.equal(prefersMarkdown("text/markdown, text/html"), true);
});

test("browser Accept header keeps getting HTML", () => {
  assert.equal(
    prefersMarkdown(
      "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    ),
    false,
  );
});

test("bare wildcard (curl default) never counts as asking for markdown", () => {
  assert.equal(prefersMarkdown("*/*"), false);
  assert.equal(prefersMarkdown("text/*"), false);
});

test("missing or empty header gets HTML", () => {
  assert.equal(prefersMarkdown(null), false);
  assert.equal(prefersMarkdown(""), false);
});

test("q-values are honored", () => {
  assert.equal(prefersMarkdown("text/markdown;q=0.9, text/html"), false);
  assert.equal(prefersMarkdown("text/markdown, text/html;q=0.5"), true);
  assert.equal(prefersMarkdown("text/markdown;q=0"), false);
});

test("markdown beats html wildcard match", () => {
  // */* gives html q=1 by wildcard, but explicit markdown q=1 ties -> markdown.
  assert.equal(prefersMarkdown("text/markdown, */*"), true);
  // Explicit html above markdown wins.
  assert.equal(prefersMarkdown("text/html, text/markdown;q=0.8"), false);
});

test("parseAccept handles whitespace, params, and malformed q", () => {
  assert.deepEqual(parseAccept(" text/markdown ; q=0.5 , text/html"), [
    { type: "text/markdown", q: 0.5 },
    { type: "text/html", q: 1 },
  ]);
  // Malformed q falls back to 1; out-of-range q is clamped.
  assert.deepEqual(parseAccept("text/markdown;q=abc"), [
    { type: "text/markdown", q: 1 },
  ]);
  assert.deepEqual(parseAccept("text/markdown;q=7"), [
    { type: "text/markdown", q: 1 },
  ]);
});
