import { expect, test, type Page, type Route } from "@playwright/test";

const definition = {
  schema_version: "ets.connector.definition.v1",
  connector_id: "native.syslog",
  display_name: "Syslog TLS",
  description: "Frozen baseline native syslog fixture.",
  implementation_class: "native",
  source_classes: ["syslog"],
  adapter_version: "1.0",
  sdk_contract_version: "ets.connector.sdk.v1",
  capture_envelope_versions: ["ets.capture.v1"],
  gateway_host_versions: ["ets.gateway.connector-host.v1"],
  capabilities: {
    delivery_modes: ["push"],
    authentication_methods: ["none"],
    discovery: false,
    checkpointing: false,
    reconciliation: true,
    normalization: true,
    health: true,
  },
  configuration_schema: {
    instance_schema: "ets.connector.instance.v1",
    settings_schema_ref: null,
  },
};

const instance = {
  schema_version: "ets.connector.instance.v1",
  instance_id: "native-syslog-01",
  connector_id: "native.syslog",
  connector_version: "1.0",
  enabled: true,
  scope: { tenant_id: "tenant-demo", workspace_id: "workspace-alpha" },
  source: { name: "Frozen syslog", environment: "production" },
  authentication: { method: "none", credential_ref: null },
  collection: { mode: "push", interval_seconds: null, batch_size: 500 },
  checkpoint: { strategy: "none", durable: true },
  policy: {
    capture_profile: "capture.native.syslog.v1",
    normalization_profile: "normalize.native.syslog.v1",
  },
  retry: { max_attempts: 8, backoff: "exponential", max_age_seconds: 86400 },
  gap_detection: { enabled: true },
  settings: {
    bind_host: "0.0.0.0",
    bind_port: 6514,
    max_connections: 128,
    max_message_bytes: 65536,
    read_idle_timeout_seconds: 30,
  },
};

const record = {
  schema_version: "ets.connector.instance_record.v1",
  instance,
  revision: 1,
  created_at_utc: "2026-08-14T00:00:00Z",
  updated_at_utc: "2026-08-14T00:00:00Z",
};

const runtime = {
  schema_version: "ets.connector.runtime.v1",
  instance_id: "native-syslog-01",
  checkpoint: null,
  checkpoint_revision: 0,
  retry_count: 0,
  next_attempt_at_utc: null,
  last_success_at_utc: "2026-08-14T00:00:00Z",
  observation_state: "healthy_observation",
  gap_open: false,
  lease_owner: null,
  lease_expires_at_utc: null,
  updated_at_utc: "2026-08-14T00:00:00Z",
};

async function reply(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function installFrozenMocks(page: Page) {
  await page.route("**/api/v2/auth/context", (route) => reply(route, {
    subject: "frozen-operator@example.test",
    tenant_id: "tenant-demo",
    workspace_id: "workspace-alpha",
    roles: ["operator"],
    capabilities: ["evidence.read", "connector.manage"],
    authorization_profile: "production",
  }));
  await page.route("**/health", (route) => reply(route, { status: "ok", version: "0.1.0" }));
  await page.route("**/ready", (route) => reply(route, { ready: true }));
  await page.route("**/version", (route) => reply(route, { version: "0.1.0" }));

  await page.route("**/gateway/connectors/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path.endsWith("/catalog")) return reply(route, [definition]);
    if (path.endsWith("/instances") && request.method() === "GET") {
      return reply(route, { items: [record] });
    }
    if (path.endsWith("/instances") && request.method() === "POST") {
      return reply(route, { ...record, instance: request.postDataJSON() }, 201);
    }
    if (path.endsWith("/runtime")) return reply(route, runtime);
    if (path.endsWith("/validate")) return reply(route, {
      schema_version: "ets.connector.health.v1",
      state: "healthy",
      code: "ok",
      message: "Frozen configuration is valid",
      retry_after_seconds: null,
    });
    if (path.endsWith("/test-connection")) return reply(route, {
      schema_version: "ets.connector.health.v1",
      state: "healthy",
      code: "ok",
      message: "Frozen source connection succeeded",
      retry_after_seconds: null,
    });
    return reply(route, { detail: `Unexpected ${request.method()} ${path}` }, 500);
  });
}

test("IPQ-D10 frozen guided operator workflow reaches activation without raw file editing", async ({ page }) => {
  await installFrozenMocks(page);
  await page.goto("/collectors");
  await expect(page.getByRole("heading", { name: "Connector operations" })).toBeVisible();
  await page.getByRole("button", { name: "Add connector" }).click();

  for (const step of ["Connection", "Scope", "Evidence policy", "Collection"] as const) {
    await expect(page.getByRole("dialog", { name: step })).toBeVisible();
    await page.getByRole("button", { name: "Continue" }).click();
  }

  await expect(page.getByRole("dialog", { name: "Test" })).toBeVisible();
  await expect(page.getByText("pre-commit evidence candidate", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "Validate configuration" }).click();
  await expect(page.getByText("Frozen configuration is valid")).toBeVisible();
  await page.getByRole("button", { name: "Continue" }).click();

  await expect(page.getByRole("dialog", { name: "Activate" })).toBeVisible();
  await page.getByRole("checkbox", {
    name: "I understand activation enables the configured source collection path.",
  }).check();
  await page.getByRole("button", { name: "Activate connector" }).click();
  await expect(page.locator("aside.connector-drawer")).toBeVisible();
  await expect(page.getByText("Operational health is not ETS cryptographic verification", { exact: false })).toBeVisible();
});

test("IPQ-D13 frozen modal receives deterministic keyboard focus and Escape return", async ({ page }) => {
  await installFrozenMocks(page);
  await page.goto("/collectors");
  const add = page.getByRole("button", { name: "Add connector" });
  await add.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog", { name: "Connection" })).toBeVisible();
  const close = page.getByRole("button", { name: "Close connector wizard" });
  await expect(close).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog", { name: "Connection" })).toHaveCount(0);
  await expect(add).toBeFocused();
});

test("IPQ-D13 frozen status and theme semantics are visible in browser", async ({ page }) => {
  await installFrozenMocks(page);
  await page.goto("/collectors");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.getByRole("cell", { name: "Enabled" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "Healthy" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "No open gap" })).toBeVisible();
  const light = page.getByRole("button", { name: "Light" });
  await light.focus();
  const outline = await light.evaluate((element) => getComputedStyle(element).outlineStyle);
  expect(outline).not.toBe("none");
  await page.keyboard.press("Enter");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});

test("IPQ-D13 frozen narrow viewport keeps authorization state visible", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await installFrozenMocks(page);
  await page.goto("/collectors");
  await expect(page.getByText("Server authorized", { exact: false })).toBeVisible();
});
