# ETS Fleet Dark Pro C1

Status: implementation candidate for FLEET-C1 / #517 under FLEET-C / #483.

## Purpose

FLEET-C1 creates the first authenticated Lantern Fleet operator surface on top of the merged ETS Fleet enrollment and presence runtime. It is intentionally read-only.

The portal is a **backend-for-frontend (BFF)**. The browser receives only sanitized Fleet read models and static UI assets. The browser never receives IoT Hub service credentials, DPS credentials, device private keys, device reusable credentials, Core/Gateway credentials, Azure management tokens, signing keys, or raw customer evidence.

Target production hostname remains `fleet.lanternprotocol.net`.

## Truth boundaries

C1 preserves the Fleet architectural separation already established by FLEET-B:

- authoritative ETS enrollment/lifecycle state;
- provider transport presence;
- ETS signed-heartbeat freshness;
- certificate/attestation posture;
- software/profile version;
- evidence verification;
- semantic device health.

**Presence is not health.** `transport_presence=online` says only that the accepted transport signal currently classifies the device as online. It does not prove the device is uncompromised, functioning correctly, complete, or compliant.

**Heartbeat is not evidence verification.** A current signed heartbeat indicates an authorized credential recently produced an accepted heartbeat under Fleet policy. It does not verify the device's evidence stream or establish semantic truth.

C1 therefore has no generic `healthy`, `trusted`, or universal trust-score field. API responses explicitly retain `evidence_verified=false` and `health_asserted=false` where a consumer might otherwise infer those claims.

## Authorization model

The portal uses three Fleet application roles:

- `Fleet.Viewer`
- `Fleet.Operator`
- `Fleet.SecurityAdmin`

C1 exposes only read routes, so all three roles map to `fleet.read`; higher roles also receive server-derived capabilities reserved for later mutation slices.

`principal_from_entra_claims()` accepts only exact Fleet app-role names from **already validated** Microsoft Entra claims. JWT signature, issuer, audience, expiry, Conditional Access, and session validation remain responsibilities of the production authentication boundary.

ETS tenant/workspace authorization is deliberately **not** accepted from arbitrary browser headers or generic token capabilities. The hosting composition resolves authorized `ScopeBinding` values server-side and supplies them when creating `FleetPrincipal`.

Every device list/detail operation filters by those server-owned scope bindings. An unauthorized device ID and an unknown device ID both return the same sanitized 404 response to avoid IDOR existence leakage.

## Read model

`FleetPortalService` builds a sanitized current-device view from:

1. a `FleetEnrollmentReader`, and
2. a `FleetPresenceSnapshotReader`.

The in-memory enrollment reference store now provides `list_current_enrollments()` as a read-side snapshot helper without changing the authoritative `EnrollmentStore` write protocol.

Presence is read through `snapshot(device_id, now=...)`, which means heartbeat stale/current posture is recomputed from trusted service time instead of copying a persisted `current` value forever.

### Overview

The overview keeps separate counts for:

- total visible devices;
- enrolled lifecycle state;
- transport online/offline/unknown;
- heartbeat current/stale/missing;
- quarantined;
- revoked;
- expiring X.509 certificates;
- hardware-attested devices;
- explicitly non-hardware-attested/software-demo devices.

### Device list

The device list exposes bounded operational metadata:

- canonical ETS device ID;
- bounded friendly name;
- product/profile;
- authorized tenant/workspace;
- lifecycle state;
- transport presence;
- heartbeat posture;
- certificate posture;
- attestation class and hardware-attested flag;
- software/profile version;
- last accepted transport/heartbeat receipt timestamps.

### Device detail

Device detail additionally exposes non-secret identity metadata needed for operator diagnostics:

- enrollment ID;
- authentication method;
- public-key fingerprint SHA-256;
- key-custody class;
- provisioning backend identifier;
- superseded enrollment reference when present.

The public-key fingerprint is an identifier, not a private key or reusable credential. It is omitted from the fleet list and shown only on the authorized detail view.

## Browser/BFF boundary

`build_fleet_portal_router()` requires a server-supplied `PrincipalResolver`. It does not parse browser-supplied `Authorization`, tenant, workspace, capability, or administrative scope headers itself.

All Fleet portal routes require an authenticated principal, including static portal assets.

The BFF exposes:

- `GET /fleet`
- `GET /fleet/`
- `GET /fleet/assets/app.css`
- `GET /fleet/assets/app.js`
- `GET /fleet/bff/v1/session`
- `GET /fleet/bff/v1/overview`
- `GET /fleet/bff/v1/devices`
- `GET /fleet/bff/v1/devices/{device_id}`

C1 intentionally exposes no POST, PUT, PATCH, or DELETE route.

Query bounds are enforced server-side. Device pages permit `limit` from 1 through 100 and bounded offsets.

## Browser security

Fleet responses use a consistent restrictive header profile:

- `Cache-Control: no-store`;
- HSTS;
- CSP with `default-src 'self'`, `base-uri 'none'`, `frame-ancestors 'none'`, and no inline script/style allowance;
- `X-Frame-Options: DENY`;
- `X-Content-Type-Options: nosniff`;
- `Referrer-Policy: no-referrer`;
- restrictive Permissions Policy;
- same-origin opener/resource policy.

The Dark Pro shell contains no inline JavaScript or CSS. The script and stylesheet are separate authenticated same-origin routes.

JavaScript renders device-controlled strings with DOM `textContent` and `replaceChildren`; it does not use `innerHTML`. A malicious friendly name therefore remains text rather than executable markup.

The UI uses neither `localStorage` nor `sessionStorage`. Light mode is supported as an in-memory presentation toggle; dark mode remains the default.

## Accessibility

The C1 shell targets WCAG 2.2 AA fundamentals:

- semantic headings and table structure;
- keyboard-operable buttons;
- visible focus treatment;
- skip navigation;
- status messages with `aria-live`;
- status labels contain text and do not rely on color alone;
- horizontal table overflow remains keyboard focusable;
- responsive device detail layout.

Formal browser accessibility qualification should be added to the deployed portal slice before production activation.

## Friendly-name handling

Enrollment metadata can carry a bounded `friendly_name`. The server removes ASCII control characters, trims whitespace, and limits it to 128 characters. It does not attempt to convert HTML into trusted markup.

The browser always renders the value using `textContent`, providing the actual output-encoding boundary for `<script>`, event-handler, and other markup-shaped strings.

## C1 security qualification

Tests cover:

- missing authenticated principal;
- unsupported/forged Fleet role;
- server-derived role capabilities;
- server-owned scope filtering;
- cross-tenant/workspace access denial;
- IDOR existence suppression;
- read-time heartbeat staleness;
- malicious friendly-name handling;
- bounded query pagination;
- no secret-bearing output patterns;
- CSP/no-store/clickjacking headers;
- no inline JavaScript/style;
- no `innerHTML`, `localStorage`, or `sessionStorage`;
- no Azure SDK/Core/Edge/Gateway coupling;
- no IoT Hub twin `connectionState` truth;
- read-only route architecture.

## Production composition

C1 is a portal/BFF contract, not a production Azure deployment by itself.

Production composition should be:

`Browser -> approved Azure public edge/WAF -> Entra-authenticated Fleet BFF -> private Fleet service/data plane`

The Entra boundary must validate issuer, audience, signature, token/session expiry, and policy before the `PrincipalResolver` returns a principal. Scope authorization must come from a company-controlled ETS mapping rather than browser-provided tenant/workspace headers.

No direct browser route to IoT Hub, DPS, Azure Resource Manager, Core, Gateway, Edge management, or Fleet storage is permitted.

## C2 handoff

FLEET-C2 should add the privileged mutation boundary:

- enrollment pre-authorization/approval where policy requires;
- quarantine;
- revoke;
- decommission;
- certificate rotation orchestration;
- notification-policy administration;
- sanitized audit export.

Those operations require additional controls not needed for C1 reads:

- CSRF protection;
- `Fleet.Operator` / `Fleet.SecurityAdmin` capability checks;
- destructive-action confirmation;
- recent-authentication or step-up/PIM/JIT integration where available;
- optimistic concurrency/idempotency;
- bounded administrative ETS evidence for trust-changing actions;
- no secret/customer-payload material in audit records.

C1 must not be represented as providing those destructive controls until C2 is separately implemented and qualified.
