# ETS Console

ETS Console is the production-oriented browser surface for ETS operators, investigators, architects,
auditors, and evidence producers. It is intentionally separate from `apps/observatory`, which
remains a research and demonstration environment.

## Current production shell

The current Console entrypoint uses the authenticated production shell rather than the original P1
placeholder shell.

It now provides:

- server-derived identity, tenant/workspace scope, roles, and capabilities through
  `GET /api/v2/auth/context`;
- no editable tenant/workspace control in the production entrypoint;
- role/capability-aware navigation;
- Overview and runtime diagnostics;
- direct evidence lookup and evidence detail;
- browser file registration through `POST /evidence/register` using the authenticated subject as the
  actor claim while the API still enforces authoritative scope server-side;
- artifact receipt display, proof retrieval, and proof JSON export;
- Dark Pro connector administration with dark mode by default and supported light mode;
- native and enterprise connector catalog/instance views through the versioned G2C API;
- an executive connector summary without an opaque trust score;
- guided Connection → Scope → Evidence policy → Collection → Test → Activate configuration;
- explicit source → policy → normalization → ETS evidence-candidate preview before commitment;
- known-gap visibility and reconciliation controls;
- explicit separation of source/connector health from ETS cryptographic verification.

Reusable connector credentials are not displayed by the Console. Connector configuration carries
only opaque credential references accepted by the G2B credential layer.

## Local development

The Console is a Vite application on port `5174`.

The default development proxy expects:

- evidence/API service at `http://127.0.0.1:8000`;
- authenticated Gateway management service at `http://127.0.0.1:8001`.

Start the evidence API from the repository root:

```bash
python -m uvicorn ets.api.app:app --reload --port 8000
```

`ets.gateway.management_host.create_gateway_management_app(...)` is the authenticated Gateway
management application factory. It intentionally requires an injected `ConnectorManagementService`;
there is no anonymous or browser-trusting fallback composition.

For the `local_header` management profile only, the browser may supply development scope headers.
Set these before starting Vite:

```bash
VITE_ETS_LOCAL_TENANT=tenant_demo
VITE_ETS_LOCAL_WORKSPACE=workspace_alpha
```

On PowerShell:

```powershell
$env:VITE_ETS_LOCAL_TENANT = "tenant_demo"
$env:VITE_ETS_LOCAL_WORKSPACE = "workspace_alpha"
```

Then run the Console with the committed lockfile:

```bash
cd apps/console/web
npm ci
npm run dev
```

Open `http://127.0.0.1:5174/`.

The local-header profile is explicitly reported as `local_nonproduction` in the authorization
context and in the UI. Production deployments must use a qualified production auth profile and
server-derived subject/scope. `VITE_ETS_LOCAL_TENANT` and `VITE_ETS_LOCAL_WORKSPACE` are development
compatibility variables, not production trust inputs.

If the Gateway management API is deployed on a separate production origin, set
`VITE_ETS_MANAGEMENT_BASE` at build time to that trusted origin and apply the deployment's approved
browser/CORS policy. Same-origin reverse-proxy deployment remains preferred where practical.

## Connector authorization boundary

The current G2C management service enforces connector administration with management authority.
Until #293 separates read-only `connector.read` from `connector.manage`, the production Console
therefore exposes the Connectors route only when `connector.manage` is present. This is intentionally
fail-closed; the UI does not reinterpret read authority as mutation authority.

## Verification boundary

ETS can verify declared cryptographic and provenance properties of submitted records and supplied
proof material. Console must not represent registration, hashing, source health, connector health,
proof validity, or service health as proof of real-world truth, observation completeness, legal
admissibility, or regulatory compliance.

The connector preview is pre-commit. It is not a proof, verification result, or assertion that a
source record is complete or true.

## Qualification status

The repository's Python architecture tests enforce the production Console trust boundary, including
server-derived scope, versioned G2C paths, no hardcoded production operator, no raw connector-settings
JSON editor fallback, and explicit pre-commit preview language.

The Console package now has a committed npm v3 lockfile generated and built on Node 22. The dedicated
`Console Build` workflow is read-only and uses `npm ci` followed by the TypeScript/Vite production
build, so frontend dependency resolution is reproducible in pull-request qualification.

## Remaining P1 / Dark Pro work

- complete hosted production sign-in/deployment composition and browser policy;
- complete accessibility and end-to-end browser qualification;
- finish evidence inventory/list filtering and explicit proof verification reason-code rendering;
- land #293 so auditor/read-only connector visibility can use `connector.read` without mutation
  authority;
- continue connector-specific UX profiles as qualified connector packages are added;
- implement issue #210 Web Collector behind the reserved `/collect/url` workflow.
