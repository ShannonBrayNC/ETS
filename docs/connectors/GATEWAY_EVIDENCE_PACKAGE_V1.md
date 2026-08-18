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
- connector-management instance ID when that identity was committed with the event;
- authoritative Gateway source ID;
- source system;
- source record ID; and
- connector transformation profile.

Package validation cross-checks these values against provenance already committed inside the hashed
ETS event. A mismatched tenant/workspace, adapter, committed connector instance, source ID, source
system, source record, or transformation profile fails closed. If the event contains a committed
connector instance ID, the package must carry that same ID; it cannot silently omit known instance
provenance.

The connector instance and authoritative Gateway source are deliberately distinct identities. A
normal `GatewayConnectorCollectionRunner` pass commits `instance.instance_id` into capture metadata,
which becomes hashed `EvidenceEvent` provenance. The package never infers the instance ID from the
Gateway `source_id`.

Direct connector-ingress paths that do not originate from a managed connector instance may omit
`connector_instance_id`. Such a package can still carry and verify its proof, but it cannot attach an
instance-scoped gap declaration because the event contains no authoritative instance binding.

Adding connector instance provenance does **not** alter the connector candidate's committed source-
content representation or its content digest. This preserves duplicate/replay compatibility for
source records committed before instance provenance was introduced. A legacy event that lacks the
new instance binding cannot be retroactively assigned an instance-scoped gap declaration.

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
`affects_cryptographic_verification` to `false`. A gap declaration is accepted only when its source
system and connector instance both match event-bound package provenance, its detection timestamp is
not after package export, and its latest `updated_at_utc` state was known by export time. A gap from
another SharePoint connector instance therefore cannot be attached merely because both instances
share the same Microsoft source family.

## Export snapshot time

`exported_at_utc` describes the package snapshot, so it must not precede either the committed event
or the proof tree head embedded in the package. Gap state updated after `exported_at_utc` is rejected
rather than being represented as if the future operational state were known when the package was
created.

These checks constrain package chronology only. They do not alter proof validity or claim that ETS
controls the source system's original event time.

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
