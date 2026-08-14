# ETS Connector SDK v1

Status: GATE-G2A implementation candidate
Contract: `ets.connector.sdk.v1`
Definition schema: `ets.connector.definition.v1`
Instance schema: `ets.connector.instance.v1`
Capture contract: `ets.capture.v1`

## Purpose

ETS Connector SDK v1 defines the product-neutral contract used by native Gateway ingestion connectors and enterprise source adapters. It standardizes connector metadata, customer connector instances, adapter capabilities, configuration validation, source checkpoints, reconciliation status, normalized pre-commit evidence candidates, and connector health.

The SDK does **not** define ETS canonicalization, hashing, Merkle construction, proof semantics, signing, tenant authorization, or Gateway persistence. Those remain outside the connector boundary.

## Boundary and trust model

A connector is an observation adapter, not an authority. The runtime must preserve these boundaries:

1. A connector instance may request a tenant/workspace scope, but authenticated Gateway management/source authorization remains authoritative.
2. A source API response, webhook acceptance, or adapter collection result is not an ETS commitment receipt.
3. Connector checkpoints and reconciliation state are source-observation state and must remain separate from ETS canonical/Merkle state.
4. Connector code receives no production evidence-signing private key through the SDK.
5. Capture/minimization/redaction policy is orchestrated outside the adapter before immutable ETS commitment.
6. `ConnectorEvidenceCandidateV1` intentionally has no tenant/workspace, Merkle, proof, signature, signer, or checkpoint fields. Extra fields fail strict validation.
7. Connector operational health is not evidence verification status.

## Connector definition

A connector definition is shipped/versioned product metadata. It declares:

- stable `connector_id`;
- implementation class (`native`, `enterprise_api`, `generic`, or `third_party`);
- adapter version;
- SDK contract version;
- supported Gateway connector-host versions;
- supported capture-envelope versions;
- source classes;
- push/poll delivery modes;
- authentication methods;
- discovery/checkpoint/reconciliation/normalization/health capabilities;
- the general connector-instance schema and optional source-specific settings-schema reference.

Definitions are immutable values after validation. Duplicate ids fail closed in `ConnectorRegistry`.

## Connector instance

A connector instance is customer configuration. It includes:

- instance and connector identity/version;
- requested ETS tenant/workspace scope;
- source name/environment;
- authentication method and optional opaque `credential_ref`;
- push/poll collection settings;
- checkpoint strategy;
- capture and normalization policy references;
- retry and gap-detection policy;
- bounded source-specific `settings`.

Reusable credential values are not part of the instance contract. Exact secret-like keys such as `password`, `client_secret`, `api_key`, `token`, and `private_key` are rejected recursively from `settings`. G2B owns credential-provider resolution and lifecycle behavior.

## Adapter protocol

Every adapter implements behavior equivalent to:

- `validate_config`
- `test_connection`
- `discover`
- `collect`
- `checkpoint`
- `reconcile`
- `normalize`
- `health`

Capabilities declare whether a behavior is meaningful for a connector. Unsupported methods should fail explicitly rather than silently simulating support.

`collect` returns a bounded source batch and optional source checkpoint. The runtime must not interpret that result as successful ETS commitment. `normalize` returns `ConnectorEvidenceCandidateV1`, which is a pre-commit candidate only.

## Registry and compatibility

`ConnectorRegistry` provides deterministic definition discovery and adapter registration. It validates:

- connector id exists;
- instance adapter version equals the registered definition version;
- definition SDK contract equals the runtime SDK contract;
- the runtime Gateway connector-host version is declared by the connector;
- the runtime capture-envelope version is declared by the connector;
- requested delivery mode is declared;
- authentication method is declared.

Any mismatch raises `ConnectorCompatibilityError` and fails closed before adapter execution.

Manifest directories are loaded from sorted `*.json` files so discovery is deterministic. G2D will populate built-in production manifests under `config/connectors/builtin/`; G2A only supplies the loader and synthetic fixtures.

## Runtime states

The shared result/status vocabulary includes:

- `ok`
- `unsupported`
- `invalid_config`
- `authentication_failed`
- `authorization_failed`
- `throttled`
- `retryable_error`
- `terminal_error`
- `gap_detected`
- `unknown_observation`
- `incompatible_version`

These are connector/runtime states, not ETS verification outcomes.

## Conformance

`ConnectorConformanceHarness` checks the shared portion of adapter qualification:

1. registry compatibility;
2. shared + adapter-specific configuration validation;
3. normalized candidate validation at the pre-commit boundary.

Source-specific qualification still belongs to the connector implementation tranche. G2F/G2E adapters must add source-specific retry, throttling, cursor, reconciliation, privacy, and fault-injection tests.

Synthetic fixtures are stored under `tests/fixtures/connectors/v1/`. Normative schema examples live under `schemas/connectors/v1/examples/`.

## Versioning policy

`ets.connector.sdk.v1`, `ets.connector.definition.v1`, and `ets.connector.instance.v1` are independently named contracts. Backward-incompatible changes require a new version identifier. An adapter version change does not automatically change the SDK version, but the registry requires an instance to name the exact adapter version it was configured against.

The connector contract must not silently reinterpret historical ETS capture or evidence formats.
