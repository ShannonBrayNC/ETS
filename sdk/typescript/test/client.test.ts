import assert from "node:assert/strict";
import { test } from "node:test";
import { EtsApplicationError, EtsClient } from "../src/index.js";

test("capture returns committed_local receipt and sends SDK headers", async () => {
  let captured: Request | undefined;
  const fetchImpl: typeof fetch = async (input, init) => {
    captured = new Request(input, init);
    return new Response(JSON.stringify({
      event_id: "evt-ts-1",
      log_index: 0,
      event_hash: "c".repeat(64),
      tree_head: {
        tree_size: 1,
        root_hash: "b".repeat(64),
        created_at_utc: "2026-09-25T16:00:00Z",
        log_id: "ets-sdk-dev",
        signature_alg: null,
        signature: null,
        public_key_id: null
      },
      inclusion_proof_url: "/api/v1/proofs/inclusion/evt-ts-1"
    }), { status: 201, headers: { "content-type": "application/json" } });
  };

  const client = new EtsClient({
    baseUrl: "https://ets.example/",
    apiKey: "dev-key",
    tenantId: "tenant-dev",
    workspaceId: "default",
    fetchImpl,
  });

  const receipt = await client.capture({ event_id: "evt-ts-1" }, "corr-1");
  assert.equal(receipt.commitment_state, "committed_local");
  assert.equal(receipt.schema_version, "ets.sdk.event_commit_receipt.v1");
  assert.equal(captured?.headers.get("X-ETS-SDK-Contract"), "ets.application.sdk.v1");
  assert.equal(captured?.headers.get("X-ETS-API-Key"), "dev-key");
  assert.equal(captured?.headers.get("X-ETS-Tenant"), "tenant-dev");
  assert.equal(captured?.headers.get("X-Correlation-ID"), "corr-1");
});

test("bearer auth rejects tenant/workspace headers", () => {
  assert.throws(
    () => new EtsClient({
      baseUrl: "https://ets.example/",
      bearerToken: "token",
      tenantId: "tenant",
      workspaceId: "workspace"
    }),
    (error: unknown) => error instanceof EtsApplicationError && error.code === "unsafe_configuration",
  );
});
