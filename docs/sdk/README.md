# ETS Developer SDKs

Status: SDK-1 contract frozen; SDK-2/SDK-3 clients implemented; SDK-4 release preparation

Roadmap: #274

ETS exposes three deliberately separate developer surfaces.

| Surface | Contract | Audience | Authority |
| --- | --- | --- | --- |
| Application SDK | `ets.application.sdk.v1` | application developers | capture, retrieve, export, and invoke verification |
| Connector SDK | `ets.connector.sdk.v1` | source/adapter developers | observe and normalize source records before ETS commitment |
| Verifier | `ets.verifier.v1` | auditors, CI, independent systems | independently evaluate ETS evidence/proof material |

These surfaces must not be collapsed into one ambiguous "SDK." A connector is an
observer adapter, an application client is a protocol consumer, and the verifier
owns independent validation semantics.

## SDK-1 deliverables

SDK-1 freezes the first machine-readable Application SDK compatibility contract,
the local event-commit receipt, the transport-neutral error taxonomy, and the
first cross-language conformance vectors.

The existing `ets.sdk.local` facade remains supported. Python synchronous and
asynchronous remote clients and .NET/TypeScript Application clients are now
implemented against these contracts; see [Python](PYTHON_CLIENT.md) and
[cross-language scope](CROSS_LANGUAGE.md). This does not claim a strict offline
verifier implementation in each language, arbitrary-payload hashing equivalence,
or completed public registry publication. The [release process](RELEASE.md)
remains a separate gate. OpenTelemetry helpers are not established by this status.

The proposed [Desktop Developer Edition](../commercial/DESKTOP_DEVELOPER_EDITION_READINESS.md)
adds a bundled verifier, offline SDK assets and reproducible samples without
changing these contracts. Its workbench and SDK-kit export are not implemented.

## Nonclaims

An SDK receipt is not automatically proof of source truth, completeness,
authorization, synchronization, current standing, or real-world consequence.
Those claims require the corresponding ETS proof, policy, observation, and/or
standing checks.
