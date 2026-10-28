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

## Practical developer guides and test kit

- [Task-oriented API and integration reference](TASK_GUIDE.md)
- [Python local/sync/async guide](PYTHON_CLIENT.md)
- [.NET guide and installed-package quickstart](DOTNET_CLIENT.md)
- [TypeScript guide and installed-package quickstart](TYPESCRIPT_CLIENT.md)
- [PowerShell 7 REST/CLI integration examples](POWERSHELL_INTEGRATION.md)
- [Ten runnable synthetic industry recipes](INDUSTRY_COOKBOOK.md)
- [Downloadable test-kit procedure and acceptance checklist](TEST_KIT.md)

The test kit is for SDK and existing Desktop Verifier testing. It is not a
production deployment or implementation of the proposed Developer authoring UI.

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

## Nonclaims

An SDK receipt is not automatically proof of source truth, completeness,
authorization, synchronization, current standing, or real-world consequence.
Those claims require the corresponding ETS proof, policy, observation, and/or
standing checks.
