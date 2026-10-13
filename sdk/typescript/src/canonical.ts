import { createHash } from "node:crypto";

function canonicalValue(value: unknown): string {
  if (value === null || typeof value === "boolean") return JSON.stringify(value);
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new TypeError("ETS canonical JSON rejects non-finite numbers");
    return JSON.stringify(value);
  }
  if (typeof value === "string") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalValue).join(",")}]`;
  if (typeof value === "object") {
    const object = value as Record<string, unknown>;
    const keys = Object.keys(object).sort();
    return `{${keys.map((key) => `${JSON.stringify(key)}:${canonicalValue(object[key])}`).join(",")}}`;
  }
  throw new TypeError(`Unsupported ETS canonical JSON value: ${typeof value}`);
}

export function canonicalize(value: unknown): string {
  return canonicalValue(value);
}

export function canonicalSha256(value: unknown): string {
  return createHash("sha256").update(canonicalize(value), "utf8").digest("hex");
}
