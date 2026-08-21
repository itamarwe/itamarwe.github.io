import test from "node:test";
import assert from "node:assert/strict";
import { homeJsonLd } from "../lib/structured-data.ts";
import { site } from "../lib/site.ts";

test("homepage JSON-LD is a Person + WebSite graph with the required fields", () => {
  // Round-trip through JSON exactly as the page embeds it.
  const data = JSON.parse(JSON.stringify(homeJsonLd()));
  assert.equal(data["@context"], "https://schema.org");

  const graph: Array<Record<string, unknown>> = data["@graph"];
  const person = graph.find((n) => n["@type"] === "Person")!;
  const website = graph.find((n) => n["@type"] === "WebSite")!;
  assert.ok(person, "Person node present");
  assert.ok(website, "WebSite node present");

  assert.equal(person.name, site.author);
  assert.equal(person.url, `${site.url}/`);
  assert.equal(person.email, `mailto:${site.email}`);
  assert.ok(typeof person.description === "string" && person.description.length > 0);
  assert.ok(Array.isArray(person.sameAs) && (person.sameAs as string[]).length >= 2);

  assert.equal(website.name, site.title);
  assert.equal(website.url, `${site.url}/`);
  assert.deepEqual(website.author, { "@id": person["@id"] });
});
