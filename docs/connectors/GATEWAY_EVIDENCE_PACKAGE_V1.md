# Gateway Evidence Package v1

Schema identifiers:

- `ets.gateway.evidence_package.v1`
- `ets.connector.source_provenance.v1`
- `ets.connector.gap_declaration.v1`

## Purpose

This product-layer export envelope places connector source provenance and relevant collection-
continuity declarations beside an existing portable `ets.proof_bundle.v1` without changing the ETS
cryptographic verification contract.

The envelope is outside `ets-core`. `EvidenceProofBundle` remains the normative portable proof
input. Connector operational declarations are explanatory context for operators, auditors, and
release packages; they are not proof inputs and cannot turn source health into evidence truth or
completeness.

## Source provenance

`ConnectorSourceProvenanceV1` exposes the bounded connector provenance needed to interpret an
exported proof:

- ETS tenant and workspace;
- connector/adapter ID;
- authoritative Gateway source ID;
- source system;
- source record ID; and
- connector transformation profile.

Package validation cross-checks these values against provenance already committed inside the hashed
ETS event. A mismatched tenant/workspace, adapter, source ID, source system, source record, or
transformation profile fails closed.

The contract fixes `raw_source_payload_retained` to `false` and rejects a connector event whose
committed capture metadata says otherwise. The package carries references and minimized metadata,
not a second raw-source retention channel.

## Gap declarations

`ConnectorGapDeclarationV1` is intentionally minimized. It includes:

- gap and connector-instance identifiers;
- source system;
- bounded reason and lifecycle status;
- detection/update/reconciliation/resolution/acknowledgement timestamps;
- terminal outcome when known; and
- recovered-record count.

It deliberately omits free-form operator notes and acknowledgement actor identity. The Microsoft
projection helper converts a qualified `ets.connector.microsoft.reconciliation_gap.v1` record into
this minimized declaration while preserving the recovery outcome.

Every declaration fixes both `source_completeness_claimed` and
`affects_cryptographic_verification` to `false`. A gap declaration from another source system or a
gap detected after the export timestamp is rejected.

## Verification boundary

`verify_gateway_evidence_package()` delegates only the embedded `EvidenceProofBundle` to the
existing offline `verify_bundle()` verifier. The verifier continues to evaluate the committed event
hash, inclusion proof, and tree-head/root linkage exactly as before.

Changing a valid operational gap declaration does not change the cryptographic verification result.
Tampering with the embedded proof still fails even if the operational declarations otherwise look
healthy.

This separation is required by #309: package users can see source provenance and continuity limits
without reinterpreting operational state as cryptographic truth.

## Nonclaims

A successfully parsed or verified Gateway evidence package does not prove:

- Microsoft or other source-system truth;
- source or tenant completeness;
- legal admissibility;
- compliance status; or
- absence of events outside the connector's declared collection coverage.

Independent ETS proof verification remains a narrower cryptographic claim about the committed event
and append-only log evidence represented by the embedded proof bundle.
