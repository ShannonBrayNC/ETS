# ETS Fleet Enrollment Runtime v1

Status: implementation slice for #503 / FLEET-A
Parent: #481
Contract: `ets.device.enrollment.v1`

## Purpose

The Fleet enrollment runtime enforces the frozen ETS device enrollment contract before a
cloud-specific provisioning adapter is allowed to grant operational device authority. It is an
operational control-plane component, not an ETS evidence-verification dependency.

Existing ETS evidence remains independently verifiable without the Fleet service.

## Runtime boundary

The implementation lives in `ets.fleet` and deliberately separates four concerns:

1. **Canonical Fleet enrollment record** — strict, immutable, non-secret metadata matching
   `ets.device.enrollment.v1`.
2. **Provider validation port** — `EnrollmentIdentityValidator` validates X.509 chain/revocation
   or TPM attestation outside the provider-neutral state machine.
3. **Persistence port** — `EnrollmentStore` allows a durable Fleet registry to replace the
   thread-safe in-memory reference store without changing authorization semantics.
4. **Authoritative state machine** — `DeviceEnrollmentService` owns lifecycle, scope,
   authorization, replay rejection, and credential rotation.

Azure DPS/IoT Hub integration belongs behind the validator/persistence/provider adapters. Azure
resource IDs, DPS payloads, SAS material, and IoT Hub service credentials do not become canonical
ETS device identity semantics.

## Trust profiles

### Virtual Demo

A Virtual Demo enrollment may use X.509 with software-held key custody only when it declares:

- `profile=virtual_demo`
- `key_custody=software_demo`
- `hardware_attested=false`

The runtime rejects attempts to represent this profile as hardware-attested.

### Physical Pilot / Production

Physical and production-directed enrollments prohibit software-demo custody. TPM enrollment
requires all of the following together:

- `auth_method=tpm_attestation`
- `attestation_class=tpm2`
- `key_custody=tpm2`
- `hardware_attested=true`

The provider adapter must independently validate the actual TPM attestation. Contract validation
alone is not a claim that a physical TPM was observed.

## Server-authoritative scope

`tenant_id` and `workspace_id` are supplied to `DeviceEnrollmentService.submit()` as an
authoritative server-side binding. If the submitted record differs, enrollment fails with
`server_scope_mismatch` before activation.

Reconnect, authorization, and credential rotation cannot silently move a device into another
scope. A future scope-reassignment workflow must be an explicit administrative trust mutation.

## Enrollment lifecycle

The runtime enforces the frozen lifecycle:

`pending -> enrolled -> quarantined -> enrolled`

`enrolled|quarantined -> revoked -> decommissioned`

Activation is a separate operation. Invalid state transitions fail closed. Authorization evaluates
the current Fleet lifecycle before accepting a credential, so quarantine/revocation blocks the
device regardless of which credential it presents.

## Authorization decision

A device authorization request is allowed only when all of the following remain established:

- the device has a current enrollment;
- the current lifecycle state is `enrolled`;
- tenant/workspace match the server-owned binding;
- the presented public-key fingerprint matches the current credential or a still-valid rotation
  overlap credential;
- an X.509 credential with a declared expiration has not expired.

Denied decisions use bounded reason codes such as `unknown_device`, `scope_mismatch`,
`credential_mismatch`, `quarantined`, `revoked`, `credential_expired`, and
`superseded_credential`.

These are operational authorization outcomes. They do not establish source truth, observation
completeness, or validity of evidence produced by a device.

## Duplicate and replay controls

Enrollment fails closed when:

- an enrollment ID is replayed;
- the same enrollment ID is reused with different content;
- a device ID is rebound to a different key without an explicit superseding enrollment;
- a public identity already belongs to another device;
- a rotation replacement changes tenant/workspace, device identity, product, profile, auth method,
  custody, or attestation class.

Public-key ownership is not released merely because a credential is revoked. Reuse as a different
device identity requires a future explicit recovery/governance workflow.

## Credential rotation

Rotation uses a new `pending` enrollment with `supersedes_enrollment_id` pointing to the current
record. `begin_rotation()`:

1. verifies identity/scope/trust-class continuity;
2. verifies the new public key differs from the current key;
3. activates the replacement credential;
4. makes it the current credential;
5. records a bounded overlap window, default maximum 24 hours.

During the overlap, both credentials may authorize the same device/scope. After the deadline the
old credential fails with `superseded_credential` even if an operator has not yet finalized the
historical lifecycle record. `complete_rotation()` revokes the old enrollment and removes the
active overlap record.

Only one rotation may be active for a device at a time.

## Secret minimization

Enrollment records retain only public/non-secret control metadata. The model rejects secret-shaped
metadata keys and common secret-value forms including private-key PEM material, bearer values,
Shared Access Signature strings, and common password/client-secret assignments.

The Fleet runtime never needs:

- device private keys;
- symmetric/SAS device credentials;
- IoT Hub owner credentials;
- Azure management tokens;
- browser session credentials;
- customer evidence payloads.

## Provider integration contract

A future Azure implementation should provide:

- `EnrollmentIdentityValidator` backed by approved X.509 or TPM/DPS validation;
- durable `EnrollmentStore` implementation for the Fleet registry;
- Azure provisioning identifiers only as bounded provider metadata;
- management operations through Entra/managed identity where Azure supports them;
- no device-facing shared symmetric authentication path for production-directed devices.

## Qualification

`tests/unit/test_fleet_enrollment_models.py` covers schema, trust-profile, secret-minimization, and
stable identity behavior.

`tests/unit/test_fleet_enrollment_service.py` covers authorization, duplicate/replay rejection,
server scope, lifecycle, expiry, provider validation, and bounded credential rotation.

`tests/architecture/test_fleet_enrollment_runtime_boundary.py` prevents the neutral runtime from
acquiring Azure SDK, Edge, Gateway, or Core-internal coupling and locks the no-symmetric-device-auth
boundary.

## Remaining FLEET-A work

This slice intentionally does not claim live Azure DPS qualification or physical R1 attestation.
The next Fleet-A increment should implement and qualify the Azure DPS/X.509/TPM adapter against
this provider-neutral runtime, then retain sanitized evidence proving a Virtual Demo identity and a
physical-pilot hardware identity can enroll without a reusable shared device secret.
