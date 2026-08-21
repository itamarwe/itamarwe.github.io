import test from "node:test";
import assert from "node:assert/strict";
import { getPageMarkdown } from "../lib/pages.ts";

// Agents verifying site legitimacy expect substantive /about, /contact and
// /privacy pages — at least 500 characters of real content each.
for (const page of ["about", "contact", "privacy"]) {
  test(`${page} page has at least 500 chars of content`, () => {
    const md = getPageMarkdown(page);
    // Strip link targets and markup so we count prose, not URLs.
    const text = md
      .replace(/\]\([^)]*\)/g, "]")
      .replace(/[#*_>\[\]`-]/g, "")
      .replace(/\s+/g, " ")
      .trim();
    assert.ok(text.length >= 500, `${page}: only ${text.length} chars`);
  });
}

test("contact page includes the email address", () => {
  assert.ok(getPageMarkdown("contact").includes("weiss.itamar@gmail.com"));
});
