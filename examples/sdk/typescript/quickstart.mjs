/** Synthetic ETS client example. --smoke uses injected responses, never a live service. */
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { access, readFile, writeFile } from "node:fs/promises";
import { EtsApplicationError, EtsClient } from "@lanternprotocol/ets-sdk";

const LIMIT = 4 * 1024 * 1024;
const jsonResponse = (value, status = 200) => new Response(JSON.stringify(value), {
  status, headers: { "content-type": "application/json" },
});
const required = (name) => {
  const value = process.env[name];
  if (!value?.trim()) throw new Error(`Set ${name} before live capture`);
  return value;
};

// Application-level deadline and body-size policy; these are not EtsClient options.
function boundedFetch(signal) {
  return async (input, init) => {
    const response = await fetch(input, {
      ...init, redirect: "error",
      signal: AbortSignal.any([signal, AbortSignal.timeout(10_000)]),
    });
    if (!response.body) return response;
    const reader = response.body.getReader();
    const chunks = [];
    let size = 0;
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        size += value.byteLength;
        if (size > LIMIT) throw new Error("Response exceeds the sample's 4 MiB limit");
        chunks.push(value);
      }
    } finally {
      await reader.cancel();
      reader.releaseLock();
    }
    const headers = new Headers(response.headers);
    headers.delete("content-encoding");
    headers.set("content-length", String(size));
    return new Response(Buffer.concat(chunks), { status: response.status, headers });
  };
}

function liveOptions(signal) {
  const baseUrl = new URL(required("ETS_BASE_URL"));
  if (baseUrl.username || baseUrl.password || baseUrl.search || baseUrl.hash)
    throw new Error("Use an endpoint without embedded credentials, query or fragment");
  if (!baseUrl.pathname.endsWith("/")) throw new Error("ETS_BASE_URL must end with /");
  const local = process.env.ETS_ALLOW_LOCAL_DEV === "1";
  if (local && !(baseUrl.protocol === "http:" && ["localhost", "127.0.0.1"].includes(baseUrl.hostname)))
    throw new Error("Local mode accepts only an explicit HTTP loopback endpoint");
  if (!local && baseUrl.protocol !== "https:") throw new Error("Live endpoints require HTTPS");
  const apiKey = process.env.ETS_API_KEY;
  const bearerToken = process.env.ETS_BEARER_TOKEN;
  if (apiKey && bearerToken) throw new Error("Choose one authentication mode");
  if (!local && !apiKey?.trim() && !bearerToken?.trim()) throw new Error("Provide one nonempty credential");
  if (local && bearerToken) throw new Error("This sample's local mode uses development headers, not bearer scope");
  return {
    baseUrl: baseUrl.href, fetchImpl: boundedFetch(signal),
    ...(apiKey ? { apiKey } : {}), ...(bearerToken ? { bearerToken } : {}),
    ...(local ? {
      allowInsecureLoopbackHttp: true,
      tenantId: required("ETS_TENANT_ID"), workspaceId: required("ETS_WORKSPACE_ID"),
    } : {}),
  };
}

function liveEvent() {
  const content = Buffer.from("Synthetic SDK integration example\n", "utf8");
  return {
    schema_version: "ets.event.v1",
    event_id: required("ETS_EVENT_ID"), // Persist this ID before capture; never silently regenerate on retry.
    tenant_id: required("ETS_TENANT_ID"), workspace_id: required("ETS_WORKSPACE_ID"),
    evidence_id: `synthetic:${required("ETS_EVENT_ID")}`,
    event_type: "sdk.synthetic.observation", subject_ref: "synthetic:integration-example",
    content_hash: createHash("sha256").update(content).digest("hex"), content_hash_alg: "sha256",
    metadata: { synthetic: true, description: "Example observation, not a real-world claim" },
    created_at_utc: required("ETS_EVENT_TIME_UTC"), source_system: "ets-sdk-example",
  };
}

async function smokeClient(fixture) {
  const eventId = fixture.event.event_id;
  let captures = 0;
  const fetchImpl = async (input, init) => {
    const request = new Request(input, init);
    assert.equal(request.headers.get("X-ETS-SDK-Contract"), "ets.application.sdk.v1");
    assert.equal(request.headers.get("Authorization"), "Bearer synthetic-not-a-secret");
    assert.equal(request.headers.get("X-ETS-Tenant"), null);
    switch (`${request.method} ${new URL(request.url).pathname}`) {
      case "GET /health": return jsonResponse({ status: "ok", version: "0.1.0a1" });
      case "GET /version": return jsonResponse({ name: "ETS", version: "0.1.0a1", api_version: "v1" });
      case "POST /api/v1/events":
        assert.deepEqual(await request.json(), fixture.event);
        assert.equal(request.headers.get("X-Correlation-ID"), "sdk-example-correlation");
        captures += 1;
        return jsonResponse({ event_id: eventId, log_index: fixture.inclusion_proof.leaf_index,
          event_hash: fixture.event_hash, tree_head: fixture.tree_head,
          inclusion_proof_url: `/api/v1/proofs/inclusion/${eventId}` }, 201);
      case `GET /api/v1/bundles/${encodeURIComponent(eventId)}`: return jsonResponse(fixture);
      default: throw new Error("Unexpected mock request");
    }
  };
  const options = { baseUrl: "https://ets.example/", bearerToken: "synthetic-not-a-secret", fetchImpl };
  const forbidden = new EtsClient({ ...options, fetchImpl: async () => jsonResponse({
    error: { code: "ETS_AUTH_FORBIDDEN", message: "synthetic denial" },
  }, 403) });
  await assert.rejects(forbidden.health(), (error) =>
    error instanceof EtsApplicationError && error.code === "authorization_failed");
  const malformed = new EtsClient({ ...options, fetchImpl: async () => new Response("not-json") });
  await assert.rejects(malformed.health(), SyntaxError);
  return { client: new EtsClient(options), assertCaptured: () => assert.equal(captures, 1) };
}

async function main() {
  const [mode, first, second, ...extra] = process.argv.slice(2);
  if (extra.length || !["--smoke", "--live"].includes(mode) || !first || (mode === "--smoke" ? !second : second))
    throw new Error("Usage: quickstart.mjs --smoke <signed-fixture.json> <new-output.json> | --live <new-output.json>");
  const output = mode === "--smoke" ? second : first;
  try { await access(output); throw new Error("Output exists; choose a new path before capture"); }
  catch (error) { if (error.code !== "ENOENT") throw error; }
  const controller = new AbortController();
  const onInterrupt = () => controller.abort();
  process.once("SIGINT", onInterrupt);
  try {
    let client, event, assertCaptured = () => {};
    if (mode === "--smoke") {
      const bytes = await readFile(first);
      if (bytes.length > LIMIT) throw new Error("Fixture too large");
      const fixture = JSON.parse(bytes.toString("utf8"));
      ({ client, assertCaptured } = await smokeClient(fixture));
      event = fixture.event;
    } else {
      client = new EtsClient(liveOptions(controller.signal));
      event = liveEvent();
    }
    await client.health();
    await client.checkCompatibility();
    const receipt = await client.capture(event, "sdk-example-correlation");
    assert.equal(receipt.commitment_state, "committed_local");
    const bundle = await client.getBundle(receipt.event_id);
    const content = JSON.stringify(bundle, null, 2) + "\n";
    if (Buffer.byteLength(content) > LIMIT) throw new Error("Export exceeds sample limit");
    await writeFile(output, content, { flag: "wx", mode: 0o600 });
    assertCaptured();
    console.log(`mode=${mode === "--smoke" ? "simulated_transport" : "live_capture"}`);
    console.log("commitment_state=committed_local; independent_verification=not_performed");
    console.log(`bundle_saved=${output}`);
    if (mode === "--smoke") console.log("synthetic_success_and_error_checks=passed");
  } finally { process.removeListener("SIGINT", onInterrupt); }
}

main().catch((error) => {
  // Do not dump response bodies, credentials or arbitrary server-supplied messages.
  console.error(error instanceof EtsApplicationError
    ? `ETS failed: code=${error.code}; http=${error.statusCode ?? "none"}`
    : `Sample failed: ${error instanceof Error ? error.name : "unknown"}; inspect configuration locally`);
  process.exitCode = 1;
});
