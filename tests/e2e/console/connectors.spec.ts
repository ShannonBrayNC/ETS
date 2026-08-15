import { expect, test, type Locator, type Page, type Route } from "@playwright/test";

type Profile = "operator" | "auditor";

const definition = {
  schema_version: "ets.connector.definition.v1",
  connector_id: "native.syslog",
  display_name: "Syslog TLS",
  description: "Qualified native syslog intake.",
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

const baseInstance = {
  schema_version: "ets.connector.instance.v1",
  instance_id: "native-syslog-01",
  connector_id: "native.syslog",
  connector_version: "1.0",
  enabled: true,
  scope: { tenant_id: "tenant-demo", workspace_id: "workspace-alpha" },
  source: { name: "Datacenter syslog", environment: "production" },
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

const baseRecord = {
  schema_version: "ets.connector.instance_record.v1",
  instance: baseInstance,
  revision: 1,
  created_at_utc: "2026-08-15T01:00:00Z",
  updated_at_utc: "2026-08-15T01:00:00Z",
};

const healthyRuntime = {
  schema_version: "ets.connector.runtime.v1",
  instance_id: "native-syslog-01",
  checkpoint: null,
  checkpoint_revision: 0,
  retry_count: 0,
  next_attempt_at_utc: null,
  last_success_at_utc: "2026-08-15T01:00:00Z",
  observation_state: "healthy_observation",
  gap_open: false,
  lease_owner: null,
  lease_expires_at_utc: null,
  updated_at_utc: "2026-08-15T01:00:00Z",
};

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

async function mockConsole(page: Page, profile: Profile) {
  let record = structuredClone(baseRecord);
  const mutations: string[] = [];

  await page.route("**/api/v2/auth/context", async (route) => {
    await json(route, {
      schema_version: "ets.gateway.authorization_context.v2",
      mode: "jwt",
      subject: profile === "operator" ? "operator@example.test" : "auditor@example.test",
      tenant_id: "tenant-demo",
      workspace_id: "workspace-alpha",
      roles: [profile],
      capabilities:
        profile === "operator"
          ? ["evidence.read", "connector.read", "connector.manage"]
          : ["evidence.read", "connector.read"],
      authorization_profile: "production",
    });
  });
  await page.route("**/health", (route) => json(route, { status: "ok", version: "0.1.0" }));
  await page.route("**/ready", (route) => json(route, { ready: true }));
  await page.route("**/version", (route) => json(route, { version: "0.1.0" }));

  await page.route("**/gateway/connectors/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const method = request.method();

    if (path.endsWith("/catalog")) return json(route, [definition]);
    if (path.endsWith("/instances") && method === "GET") {
      return json(route, { items: [record] });
    }
    if (path.endsWith("/instances") && method === "POST") {
      mutations.push("create");
      const instance = request.postDataJSON();
      record = {
        ...record,
        instance,
        revision: 1,
        updated_at_utc: "2026-08-15T01:05:00Z",
      };
      return json(route, record, 201);
    }
    if (path.endsWith("/runtime") && method === "GET") return json(route, healthyRuntime);
    if (path.endsWith("/validate") && method === "POST") {
      mutations.push("validate");
      return json(route, {
        schema_version: "ets.connector.health.v1",
        state: "healthy",
        code: "ok",
        message: "Configuration is valid",
        retry_after_seconds: null,
      });
    }
    if (path.endsWith("/test-connection") && method === "POST") {
      mutations.push("test-connection");
      return json(route, {
        schema_version: "ets.connector.health.v1",
        state: "healthy",
        code: "ok",
        message: "Source connection succeeded",
        retry_after_seconds: null,
      });
    }
    if (path.endsWith("/enable") || path.endsWith("/disable")) {
      mutations.push(path.endsWith("/enable") ? "enable" : "disable");
      record = {
        ...record,
        revision: record.revision + 1,
        instance: { ...record.instance, enabled: path.endsWith("/enable") },
      };
      return json(route, record);
    }
    if (path.endsWith("/gaps/detect") || path.endsWith("/gaps/reconcile")) {
      mutations.push(path.endsWith("/gaps/detect") ? "gap-detect" : "gap-reconcile");
      return json(route, {
        ...healthyRuntime,
        observation_state: path.endsWith("/gaps/detect") ? "collection_gap" : "healthy_observation",
        gap_open: path.endsWith("/gaps/detect"),
      });
    }

    return json(route, { detail: `Unexpected mock request ${method} ${path}` }, 500);
  });

  return mutations;
}

async function focused(locator: Locator): Promise<boolean> {
  if ((await locator.count()) === 0) return false;
  return locator.evaluate((element) => document.activeElement === element);
}

async function tabTo(page: Page, locator: Locator, maxTabs = 60) {
  await expect(locator).toBeVisible();
  if (await focused(locator)) return;
  for (let index = 0; index < maxTabs; index += 1) {
    await page.keyboard.press("Tab");
    if (await focused(locator)) return;
  }
  throw new Error(`Keyboard focus did not reach ${await locator.getAttribute("aria-label") ?? await locator.textContent()}`);
}

async function pressButton(page: Page, name: string | RegExp) {
  const button = page.getByRole("button", { name });
  await tabTo(page, button);
  await page.keyboard.press("Enter");
}

test("operator completes the governed connector workflow using keyboard only", async ({ page }) => {
  const mutations = await mockConsole(page, "operator");
  await page.goto("/collectors");
  await expect(page.getByRole("heading", { name: "Connector operations" })).toBeVisible();

  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  const lightToggle = page.getByRole("button", { name: "Light" });
  await tabTo(page, lightToggle);
  const focusStyle = await lightToggle.evaluate((element) => {
    const style = getComputedStyle(element);
    return { outlineStyle: style.outlineStyle, outlineWidth: style.outlineWidth };
  });
  expect(focusStyle.outlineStyle).not.toBe("none");
  expect(focusStyle.outlineWidth).not.toBe("0px");
  await page.keyboard.press("Enter");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await expect(page.getByRole("button", { name: "Dark" })).toBeVisible();

  const add = page.getByRole("button", { name: "Add connector" });
  await tabTo(page, add);
  await page.keyboard.press("Enter");
  const dialog = page.getByRole("dialog", { name: "Connection" });
  await expect(dialog).toBeVisible();
  const close = page.getByRole("button", { name: "Close connector wizard" });
  await expect(close).toBeFocused();

  await page.keyboard.press("Shift+Tab");
  await expect(page.getByRole("button", { name: "Continue" })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(close).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(add).toBeFocused();

  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog", { name: "Connection" })).toBeVisible();
  await pressButton(page, "Continue");
  await expect(page.getByRole("dialog", { name: "Scope" })).toBeVisible();
  await pressButton(page, "Continue");
  await expect(page.getByRole("dialog", { name: "Evidence policy" })).toBeVisible();
  await expect(page.getByLabel("Capture profile")).toHaveValue("capture.native.syslog.v1");
  await pressButton(page, "Continue");
  await expect(page.getByRole("dialog", { name: "Collection" })).toBeVisible();
  await pressButton(page, "Continue");
  await expect(page.getByRole("dialog", { name: "Test" })).toBeVisible();
  await pressButton(page, "Validate configuration");
  await expect(page.getByText("Configuration is valid")).toBeVisible();
  await pressButton(page, "Continue");
  await expect(page.getByRole("dialog", { name: "Activate" })).toBeVisible();

  const confirmation = page.getByRole("checkbox", {
    name: "I understand activation enables the configured source collection path.",
  });
  await tabTo(page, confirmation);
  await page.keyboard.press("Space");
  await expect(confirmation).toBeChecked();
  await pressButton(page, "Activate connector");

  await expect(page.getByRole("dialog", { name: "Connector details" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Close connector details" })).toBeFocused();
  expect(mutations).toContain("validate");
  expect(mutations).toContain("create");
});

test("read-only auditor can inspect connector posture but cannot mutate", async ({ page }) => {
  const mutations = await mockConsole(page, "auditor");
  await page.goto("/collectors");

  await expect(page.getByText("Read-only connector access is active.", { exact: false })).toBeVisible();
  await expect(page.getByText("Read-only auditor")).toBeVisible();
  await expect(page.getByRole("button", { name: "Add connector" })).toHaveCount(0);
  await expect(page.getByText("Inspection only")).toBeVisible();
  await expect(page.getByRole("cell", { name: "Healthy" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "No open gap" })).toBeVisible();

  const inspect = page.getByRole("button", { name: "Inspect" });
  await tabTo(page, inspect);
  await page.keyboard.press("Enter");
  const drawer = page.getByRole("dialog", { name: "Connector details" });
  await expect(drawer).toBeVisible();
  await expect(page.getByRole("button", { name: "Close connector details" })).toBeFocused();
  await expect(drawer.getByRole("button", { name: "Edit configuration" })).toHaveCount(0);
  await expect(drawer.getByRole("button", { name: "Test connection" })).toHaveCount(0);
  await expect(drawer.getByRole("button", { name: /Activate|Disable/ })).toHaveCount(0);
  await expect(drawer.getByRole("button", { name: /gap/i })).toHaveCount(0);
  expect(mutations).toEqual([]);

  await page.keyboard.press("Escape");
  await expect(drawer).toHaveCount(0);
  await expect(inspect).toBeFocused();
});

test("connector statuses and controls have semantic non-color meaning", async ({ page }) => {
  await mockConsole(page, "operator");
  await page.goto("/collectors");

  await expect(page.getByRole("table")).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Observation" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "Enabled" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "Healthy" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "No open gap" })).toBeVisible();
  await expect(page.getByText("Server authorized", { exact: false })).toBeVisible();

  await pressButton(page, "Add connector");
  await expect(page.getByRole("dialog", { name: "Connection" })).toBeVisible();
  await expect(page.getByLabel("Connector type")).toBeVisible();
  await expect(page.getByLabel("Instance ID")).toBeVisible();
  await expect(page.getByLabel("Source name")).toBeVisible();
  await expect(page.getByLabel("Environment")).toBeVisible();
  await expect(page.getByLabel("Authentication method")).toBeVisible();
  await expect(page.getByLabel("Credential reference")).toBeVisible();
});

test("narrow viewport keeps connector posture and authorization context available", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockConsole(page, "auditor");
  await page.goto("/collectors");

  await expect(page.getByRole("heading", { name: "Connector operations" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Connectors" })).toBeVisible();
  await expect(page.getByText("Server authorized", { exact: false })).toBeVisible();
  await expect(page.getByText("Read-only auditor")).toBeVisible();
  await expect(page.getByRole("cell", { name: "Healthy" })).toBeVisible();
});
