import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { canonicalize, canonicalSha256 } from "../src/canonical.js";

function repositoryRoot(): string {
  let current = fileURLToPath(new URL(".", import.meta.url));
  for (let i = 0; i < 8; i += 1) {
    const vector = join(current, "conformance", "sdk", "v1", "canonicalization", "basic.json");
    try {
      readFileSync(vector);
      return current;
    } catch {
      current = join(current, "..");
    }
  }
  throw new Error("Could not locate ETS repository root");
}

for (const relative of ["canonicalization/basic.json", "event-hashing/basic.json"]) {
  test(`Application SDK conformance: ${relative}`, () => {
    const root = repositoryRoot();
    const vector = JSON.parse(readFileSync(join(root, "conformance", "sdk", "v1", relative), "utf8")) as {
      input?: unknown;
      hashable_payload?: unknown;
      canonical_utf8: string;
      sha256: string;
    };
    const value = vector.input ?? vector.hashable_payload;
    assert.equal(canonicalize(value), vector.canonical_utf8);
    assert.equal(canonicalSha256(value), vector.sha256);
  });
}
