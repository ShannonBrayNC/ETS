# ETS Connector Credential Provider v1

Status: GATE-G2B implementation candidate

## Purpose

The connector credential-provider boundary resolves opaque connector credential references into short-lived runtime material without placing reusable values in connector configuration or management responses.

This boundary is separate from Gateway administration and ETS evidence signing.

## Trust domains

Connector source authentication, Gateway administration, and ETS evidence-signing material are separate trust domains. A connector provider must not import ETS Core signing implementations, Gateway source authorization state, or Edge product packages.

## References

Connector instances carry an opaque provider reference. References are URI-like locators with a provider scheme and provider-local identifier. User-information, query, and fragment components are rejected to reduce the risk of embedding reusable data in configuration.

## Provider contract

All providers implement `describe` and `resolve`. Providers that support lifecycle operations may additionally implement `create`, `rotate`, and `revoke`.

`describe` returns management-safe metadata only. `resolve` returns a runtime-only `CredentialLease` whose representation is redacted and whose internal buffer is overwritten when the lease is closed.

## Local pilot provider

`LocalSealedCredentialProvider` delegates persistence and sealing to two injected host boundaries:

- `SealedCredentialBackend` persists opaque sealed records.
- `CredentialSealCodec` performs host/device-specific sealing and unsealing.

The ETS package does not implement a software fallback pretending to provide hardware-backed sealing. Physical Gateway pilots should bind the codec/backend to the approved TPM or equivalent host implementation.

## Lifecycle and audit

Create, rotate, revoke, and failed resolution operations may emit `CredentialAuditEventV1`. Audit events carry a SHA-256 fingerprint of the reference instead of the reusable runtime value. Rotation increments provider-local version metadata and does not interact with historical ETS evidence.

## Failure behavior

Credential resolution fails closed for missing, expired, revoked, incompatible, or unavailable references. G2C must resolve required credentials before starting a source collection attempt; a credential failure must not advance a connector source cursor/checkpoint.

## Enterprise providers

Azure Key Vault, AWS Secrets Manager, HashiCorp Vault, and other external stores implement the same read/resolve contract through provider-specific adapters. Existing ETS Azure tree-head signer code is not a connector credential provider and must remain in its signing trust boundary.
