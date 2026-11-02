// Support directory and contacts: only verified, well-formed entries are ever shown. Run: npm test
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { filterProviders, INTERNATIONAL_DIRECTORY, URGENT_INDIA, verifiedProviders, VERIFY_LINKS } from "./support.ts";

const here = dirname(fileURLToPath(import.meta.url));
const data = JSON.parse(readFileSync(join(here, "../data/providers.json"), "utf8"));

const valid = { id: "x", name: "Example Hospital", type: "Hospital / institute", specialties: ["Psychiatry"], city: "Pune",
  region: "Maharashtra", country: "India", sourceUrl: "https://example.org/", verifiedOn: "2026-11-02" };

test("entries without an official source or verification date are never shown", () => {
  assert.equal(verifiedProviders([valid]).length, 1);
  assert.equal(verifiedProviders([{ ...valid, sourceUrl: undefined }]).length, 0);
  assert.equal(verifiedProviders([{ ...valid, sourceUrl: "http://insecure.example" }]).length, 0);
  assert.equal(verifiedProviders([{ ...valid, verifiedOn: "recently" }]).length, 0);
  assert.equal(verifiedProviders([{ ...valid, type: "Healer" }]).length, 0);
  assert.equal(verifiedProviders([null, "x", 3]).length, 0);
});

test("every entry in providers.json is valid", () => {
  assert.ok(Array.isArray(data.providers));
  assert.equal(verifiedProviders(data.providers).length, data.providers.length);
  assert.equal(new Set(data.providers.map((p: { id: string }) => p.id)).size, data.providers.length);
});

test("provider filters", () => {
  const list = verifiedProviders([valid, { ...valid, id: "y", type: "Psychiatrist", city: "Delhi", region: "Delhi", specialties: ["Child psychiatry"] }]);
  assert.equal(filterProviders(list, {}).length, 2);
  assert.equal(filterProviders(list, { location: " pune" }).length, 1);
  assert.equal(filterProviders(list, { location: "india" }).length, 2);
  assert.equal(filterProviders(list, { type: "Psychiatrist" })[0].id, "y");
  assert.equal(filterProviders(list, { specialty: "Psychiatry" })[0].id, "x");
  assert.equal(filterProviders(list, { location: "Mumbai" }).length, 0);
});

test("urgent contacts and links cite https sources", () => {
  for (const h of URGENT_INDIA) assert.ok(h.numbers.length && h.sourceUrl.startsWith("https://"), h.name);
  assert.deepEqual(URGENT_INDIA.flatMap((h) => h.numbers), ["112", "14416", "1-800-891-4416"]);
  assert.ok(INTERNATIONAL_DIRECTORY.url.startsWith("https://"));
  assert.ok(VERIFY_LINKS.every((v) => v.url.startsWith("https://")));
});
