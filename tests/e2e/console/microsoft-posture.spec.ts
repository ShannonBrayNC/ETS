import { expect, test, type Page, type Route } from "@playwright/test";

const instanceId = "microsoft-sharepoint-prod";

const definition = {
  schema_version: "ets.connector.definition.v1",
  connector_id: "microsoft.sharepoint.onedrive_delta",
  display_name: "Microsoft SharePoint / OneDrive",
  description: "Qualified Microsoft Graph metadata delta connector.",
  implementation_class: "enterprise_api",
  source_classes: ["sharepoint", "onedrive"],
  adapter_version: "1.0",
  sdk_contract_version: "ets.connector.sdk.v1",
  capture_envelope_versions: ["ets.capture.v1"],
  gateway_host_versions: ["ets.gateway.connector-host.v1"],
  capabilities: {
    delivery_modes: ["poll"],
    authentication_methods: ["bearer"],
    discovery: false,
    checkpointing: true,
    reconciliation: true,
    normalization: true,
    health: true,
  },
  configuration_schema: {
    instance_schema: "ets.connector.instance.v1",
    settings_schema_ref: null,
  },
};

const record = {
  schema_version: "ets.connector.instance_record.v1",
  instance: {
    schema_version: "ets.connector.instance.v1",
    instance_id: instanceId,
    connector_id: definition.connector_id,
    connector_version: "1.0",
    enabled: true,
    scope: { tenant_id: "tenant-demo", workspace_id: "workspace-alpha" },
    source: { name: "SharePoint evidence library", environment: "production" },
    authentication: { method: "bearer", credential_ref: "secret://microsoft-graph-app" },
    collection: { mode: "poll", interval_seconds: 60, batch_size: 100 },
    checkpoint: { strategy: "source_cursor", durable: true },
    policy: {
      capture_profile: "capture.microsoft.sharepoint.v1",
      normalization_profile: "ets.connector.microsoft.sharepoint-onedrive-metadata.v1",
    },
    retry: { max_attempts: 8, backoff: "exponential", max_age_seconds: 86400 },
    gap_detection: { enabled: true },
    settings: { tenant_profile_id: "tenant-profile-01", scope: "drive", drive_id: "drive-01" },
  },
  revision: 3,
  created_at_utc: "2026-08-18T03:00:00Z",
  updated_at_utc: "2026-08-18T03:50:00Z",
};

const runtime = {
  schema_version: "ets.connector.runtime.v1",
  instance_id: instanceId,
  checkpoint: null,
  checkpoint_revision: 4,
  retry_count: 0,
  next_attempt_at_utc: null,
  last_success_at_utc: "2026-08-18T03:58:00Z",
  observation_state: "degraded_observation",
  gap_open: true,
  lease_owner: null,
  lease_expires_at_utc: null,
  updated_at_utc: "2026-08-18T04:00:00Z",
};

const posture = {
  schema_version: "ets.connector.microsoft.operational_posture.v1",
  instance_id: instanceId,
  ets_tenant_id: "tenant-demo",
  workspace_id: "workspace-alpha",
  source_id: "microsoft-sharepoint-source",
  microsoft_tenant_id: "11111111-1111-1111-1111-111111111111",
  subscription_id: "subscription-001",
  evaluated_at_utc: "2026-08-18T04:00:00Z",
  policy_profile_id: "microsoft-prod-v1",
  health: {
    schema_version: "ets.connector.health.v1",
    state: "degraded",
    code: "gap_detected",
    message: "Microsoft Graph lifecycle state reports a possible collection gap.",
    retry_after_seconds: null,
  },
  subscription_status: "active",
  subscription_expiration_date_time: "2026-08-18T12:00:00Z",
  seconds_until_subscription_expiration: 28800,
  collection_lag_seconds: 120,
  queue_depth: 2,
  oldest_unsynchronized_age_seconds: 75,
  retryable_failure_count: 1,
  terminal_failure_count: 0,
  reconciliation_status: "reconciling",
  reconciliation_outcome: null,
  verification_claimed: false,
  source_truth_claimed: false,
  completeness_claimed: false,
};

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

async function mockMicrosoftConsole(page: Page): Promise<string[]> {
  const mutations: string[] = [];

  await page.route("**/api/v2/auth/context", (route) =>
    json(route, {
      schema_version: "ets.gateway.authorization_context.v2",
      mode: "jwt",
      subject: "auditor@example.test",
      tenant_id: "tenant-demo",
      workspace_id: "workspace-alpha",
      roles: ["auditor"],
      capabilities: ["evidence.read", "connector.read"],
      authorization_profile: "production",
    }),
  );
  await page.route("**/health", (route) => json(route, { status: "ok", version: "0.1.0" }));
  await page.route("**/ready", (route) => json(route, { ready: true }));
  await page.route("**/version", (route) => json(route, { version: "0.1.0" }));

  await page.route("**/gateway/connectors/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const method = request.method();
    if (method !== "GET") mutations.push(`${method} ${path}`);

    if (path.endsWith("/catalog")) return json(route, [definition]);
    if (path.endsWith("/instances")) return json(route, { items: [record] });
    if (path.endsWith("/runtime")) return json(route, runtime);
    if (path.endsWith("/microsoft/posture")) return json(route, posture);
    return json(route, { detail: `Unexpected mock request ${method} ${path}` }, 500);
  });

  return mutations;
}

test("read-only auditor sees Microsoft operational posture without mutation authority", async ({
  page,
}) => {
  const mutations = await mockMicrosoftConsole(page);
  await page.goto("/collectors");

  await expect(page.getByRole("heading", { name: "Connector operations" })).toBeVisible();
  await page.getByRole("button", { name: "Inspect" }).click();

  const drawer = page.getByRole("dialog", { name: "Connector details" });
  await expect(drawer).toBeVisible();
  const microsoft = drawer.getByRole("region", { name: "Microsoft operational posture" });
  await expect(microsoft).toBeVisible();
  await expect(microsoft.getByText("Operationally degraded")).toBeVisible();
  await expect(microsoft.getByText("gap_detected")).toBeVisible();
  await expect(microsoft.getByText("Active", { exact: true })).toBeVisible();
  await expect(microsoft.getByText("2m", { exact: true })).toBeVisible();
  await expect(microsoft.getByText("2 unsynchronized records")).toBeVisible();
  await expect(microsoft.getByText("1 retryable / 0 terminal")).toBeVisible();
  await expect(microsoft.getByText("reconciling", { exact: true })).toBeVisible();
  await expect(microsoft.getByText("microsoft-prod-v1")).toBeVisible();
  await expect(
    microsoft.getByText("ETS cryptographic verification", { exact: false }),
  ).toBeVisible();
  await expect(microsoft.getByText("source completeness", { exact: false })).toBeVisible();

  await expect(drawer.getByRole("button", { name: "Edit configuration" })).toHaveCount(0);
  await expect(drawer.getByRole("button", { name: "Test connection" })).toHaveCount(0);
  await expect(drawer.getByRole("button", { name: /Activate|Disable/ })).toHaveCount(0);
  await expect(drawer.getByRole("button", { name: /gap/i })).toHaveCount(0);
  expect(mutations).toEqual([]);
});
