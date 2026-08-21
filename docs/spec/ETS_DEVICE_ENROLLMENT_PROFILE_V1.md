# ETS Device Enrollment Profile v1

Status: Draft implementation contract
Date: 2026-08-21
Parent: #481
Related: #140, #221, #388, #480

## 1. Purpose

This profile defines the shared device identity and enrollment contract for ETS Edge,
ETS Gateway, and later Lantern Evidence Fabric devices. It freezes the identity
boundary before Azure Device Provisioning Service (DPS), Fleet presence, and portal
work proceeds.

The enrollment service is an operational control plane. It does not redefine ETS/PLVX
canonical evidence, hashing, Merkle, proof, or verification semantics, and it must not
be required for independent/offline verification of already-produced ETS evidence.

## 2. Security objective

A production-directed ETS device has one independently revocable cryptographic
identity. Compromise of one device credential must not authorize another device.
A device never receives a fleet-wide shared secret, IoT Hub owner credential, Azure
management credential, or another device's private material.

Production device private keys SHOULD be generated and retained in TPM 2.0, an HSM,
or an approved secure element. Private keys MUST be non-exportable when the selected
hardware supports non-exportable signing/authentication operations.

The Virtual Demo profile may use a software-held X.509 identity, but it MUST declare
`profile=virtual_demo`, `key_custody=software_demo`, and `hardware_attested=false`.
Software custody must never be displayed or documented as hardware attestation.

## 3. Normative enrollment record

The machine-readable record is:

`schemas/device/v1/device-enrollment.schema.json`

Its schema identifier is:

`ets.device.enrollment.v1`

The record contains only public/non-secret identity, authorization, lifecycle, and
scope metadata. It MUST NOT contain any of the following:

- private keys;
- symmetric device keys;
- SAS tokens or SAS connection strings;
- bearer/access/refresh tokens;
- TPM endorsement private material;
- certificate private-key bytes;
- Azure service credentials;
- raw attestation challenges or reusable attestation secrets;
- customer evidence payloads.

## 4. Stable identity binding

`device_id` is a durable ETS product identity. The authoritative registration service
binds that identifier to an approved public-key fingerprint or TPM attestation
identity. The device cannot choose an arbitrary `device_id` and thereby acquire an
existing device's tenant/workspace authority.

The initial recommended derivation for a newly manufactured/provisioned device is:

`ets-<product>:<stable-public-identity-derived-suffix>`

The exact suffix derivation MAY vary by supported hardware provider, but the binding
MUST be deterministic or durably recorded and MUST be collision checked before
activation. Changing the public identity is a credential rotation/recovery operation,
not an implicit new binding.

`public_key_fingerprint_sha256` is the lowercase SHA-256 fingerprint of the enrolled
public key or the public key represented by the accepted X.509 identity.

## 5. Supported authentication methods

### 5.1 X.509

`auth_method=x509` is the default production-directed certificate profile when a
TPM-specific DPS attestation path is not selected.

Requirements:

- each device has a unique certificate/private key;
- private key is non-exportable when hardware permits;
- certificate chain anchors only to the approved ETS device CA hierarchy;
- certificate validity, chain, revocation, identity binding, and intended device use
  are checked before enrollment becomes active;
- `certificate_thumbprint_sha256` is required in the ETS enrollment record;
- certificate rotation produces a new enrollment lifecycle record or an explicit
  superseding relationship; silent identity replacement is prohibited.

### 5.2 TPM attestation

`auth_method=tpm_attestation` requires:

- `attestation_class=tpm2`;
- `key_custody=tpm2`;
- `hardware_attested=true`;
- accepted TPM identity/attestation through the configured provisioning backend;
- no export of a device private key into the ETS application process merely to
  satisfy an API that can use the TPM provider directly.

TPM attestation proves only the declared attestation properties. It does not prove
that every application process, source observation, or captured event is truthful or
complete.

## 6. Server-authoritative scope

`scope_binding.tenant_id` and `scope_binding.workspace_id` are assigned by the
registration/control plane. They are not accepted as authoritative because a device
submitted them in a request, certificate extension, heartbeat, source payload, or
other caller-controlled field.

A device that presents a valid cryptographic identity but attempts to operate outside
its registered scope MUST fail authorization.

Scope reassignment is an administrative trust mutation and MUST be independently
audited. It MUST NOT occur as a side effect of reconnect or certificate rotation.

## 7. Enrollment lifecycle

The normative registration states are:

`pending -> enrolled -> quarantined -> revoked -> decommissioned`

Allowed operational transitions include:

- `pending -> enrolled` after policy and identity validation;
- `enrolled -> quarantined` for investigation or bounded administrative isolation;
- `quarantined -> enrolled` only after explicit authorized release;
- `enrolled|quarantined -> revoked` when credentials/authority are withdrawn;
- `revoked -> decommissioned` after retirement/key-destruction workflow;
- certificate/key rotation while enrolled through an explicit superseding record.

A revoked or decommissioned identity MUST fail future device authorization. Automatic
re-enrollment under the same revoked credential is prohibited.

## 8. Rotation and recovery

Credential rotation MUST:

1. authenticate and authorize the rotation operation independently of the new
   credential material;
2. validate the new public identity/attestation;
3. create an explicit superseding relationship;
4. permit only a bounded overlap window when operationally required;
5. remove old authorization after the overlap window;
6. emit administrative/lifecycle evidence without secret material;
7. prove that the superseded credential cannot continue to authorize the device.

Recovery from lost/corrupt hardware identity is not silent rotation. It requires an
operator-approved recovery workflow and a new identity binding. Recovery must retain
history linking the old device registration to the recovered identity without
claiming that the new private key is the old key.

## 9. Azure implementation profile

The first Azure implementation uses:

- Azure IoT Hub for device connection identity and device-to-cloud transport;
- Azure IoT Hub Device Provisioning Service for governed provisioning;
- X.509 or TPM-backed device authentication;
- Microsoft Entra ID / managed identity for service and operator administration where
  the Azure service supports it;
- Event Grid for device connect/disconnect lifecycle events in #482;
- a separate ETS Fleet registry for the schema-defined non-secret enrollment record.

Any IoT Hub shared-access policy required only for the DPS-to-IoT-Hub platform
relationship is a service-side residual dependency. It MUST remain inaccessible to
Edge/Gateway devices, browser applications, GitHub artifacts, retained ETS evidence,
and customer operators. It is not an ETS device credential.

## 10. Enrollment protocol boundary

The ETS enrollment API/adapter MAY wrap Azure DPS, another cloud provisioning system,
or a future offline manufacturing flow. The stable ETS contract is the validated
identity/lifecycle record, not a vendor-specific DPS payload.

Vendor-specific identifiers MAY appear only as bounded metadata or internal provider
state. They MUST NOT become canonical ETS device identity semantics unless separately
versioned.

## 11. Required negative tests

The implementation must fail closed for at least:

- unknown device;
- duplicate `device_id` with a different public identity;
- duplicate public identity bound to an unauthorized second device;
- expired certificate;
- revoked certificate/device;
- untrusted certificate chain;
- certificate/device-ID mismatch;
- replayed enrollment request;
- device-supplied tenant/workspace escalation;
- TPM attestation mismatch;
- rotation race;
- old credential reuse after completed rotation;
- software-demo identity claiming `hardware_attested=true`;
- registration object containing prohibited secret-shaped fields;
- malformed/unknown schema version.

## 12. Audit and ETS evidence

Material control-plane transitions SHOULD emit bounded ETS administrative evidence,
including events equivalent to:

- `device.enrollment_authorized`;
- `device.enrolled`;
- `device.credential_rotated`;
- `device.quarantined`;
- `device.revoked`;
- `device.decommissioned`.

These records identify the actor/service, UTC time, device identity, reason code,
scope, and relevant public credential fingerprint. They must not include reusable
credential material or raw attestation secrets.

## 13. Relationship to #484 Dark Pro Edge UI

The Edge operator UI consumes only public device identity and enrollment posture:

- device ID;
- public fingerprint;
- profile/product type;
- enrollment state;
- certificate expiration/revocation posture;
- key custody/attestation class;
- last signed heartbeat state when #482 lands.

The browser must never receive a device private key, local API key, IoT Hub/DPS service
credential, or reusable fleet credential.

## 14. Exit criteria for this contract

This contract is considered frozen enough for implementation when:

- the v1 schema and this profile are independently reviewed;
- Virtual Demo and physical pilot examples conform to the same stable fields;
- production symmetric device-secret enrollment remains prohibited;
- scope is server-authoritative;
- rotation/revocation/recovery semantics are explicit;
- hardware/software attestation claims cannot be confused;
- provider-specific Azure details remain behind the stable ETS contract.
