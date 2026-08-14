# ETS Gateway Native Connector Packaging v1

Status: G2D qualified  
Parent: #249  
Implements: #253

## Purpose

Expose qualified Gateway-native ingestion modes through the shared G2 connector catalog without
creating duplicate transport, normalization, authorization, ETS commitment, proof, or synchronization
implementations.

## Built-in catalog

The v1 catalog contains four qualified native connector definitions:

- `native.webhook` — qualified G1C HTTPS/webhook runtime;
- `native.syslog` — qualified G1D RFC 5424 syslog-TLS runtime;
- `native.file_drop` — qualified G1E explicit File/Drop runtime;
- `native.otlp` — qualified G1F OTLP/HTTP and OTLP/gRPC runtimes using the shared semantic and
  commitment contracts.

Every definition validates through `ets.connector.definition.v1` and references a connector-specific
settings schema. Customer instances continue to use `ets.connector.instance.v1`.

## Ownership boundary

`NativeConnectorBinding` identifies the G1 implementation owner and declared transport profile.
The management adapter does not import or call the G1 transport implementation. It therefore cannot
become a second parser or commitment path.

The owning G1 runtime remains authoritative for:

- transport parsing/framing;
- authenticated transport principal establishment;
- source registration and tenant/workspace authorization;
- privacy/minimization and normalization;
- `ets.capture.v1` construction;
- ETS Core append;
- durable synchronization;
- transport-specific bounds and shutdown behavior.

The qualified OTLP binding points to the concrete HTTP and gRPC owners:
`ets.gateway.otlp_http/create_otlp_http_app` and
`ets.gateway.otlp_grpc/GatewayOtlpGrpcHost`.

## Management adapter behavior

`NativeConnectorAdapter` exists only to make native transports participate in the common G2A/G2C
catalog and configuration contracts.

It validates:

- connector/version compatibility through the shared registry;
- push-only collection mode;
- declared authentication mode;
- a bounded allow-list of connector-specific settings.

Polling, discovery, source checkpointing, reconciliation, and generic normalization are unsupported
for these push-native wrappers because those operations would duplicate or misrepresent the G1
runtime contract.

## Operational health

A valid connector configuration is not evidence that the underlying listener is running. Until the
concrete host supplies a runtime probe, qualified native connectors return `unknown_observation`
rather than claiming healthy transport state.

This rule applies equally to OTLP after G1F-C/D qualification. Catalog qualification means the
transport implementation and its governed evidence path have passed their qualification gates; it
does not mean a particular deployed listener is currently healthy.

## Assurance labels

Bindings declare one bounded product-facing assurance label:

- `production_preferred` — the declared secured transport profile is the preferred production path;
- `bounded_local` — a local explicit-submission boundary with qualified resource and filesystem
  controls;
- `compatibility` — reserved for explicitly lower-assurance compatibility modes.

These labels are configuration/transport metadata only. They are not verification, truth,
completeness, compliance, or legal-admissibility results.

## Credential and scope boundary

Native connector instance configuration never contains reusable credential material. Authentication
methods describe the outer transport identity mechanism, while authoritative tenant/workspace/source
scope remains server-side. Payload attributes, syslog HOSTNAME, file names, and OTLP resource fields
cannot grant ETS scope.

## Activation rule

A connector catalog entry may exist before its transport is active, but activation must fail closed
unless its G1 runtime profile has completed its own qualification. `native.otlp` transitioned to
`qualified` only after #280 and #281 completed their exact-head CI, security, formal, and independent
review gates.

## Exit gate

G2D is qualified when all four definitions validate through the shared connector registry, native
configuration cannot silently relax G1 invariants, G2C can represent their instances truthfully, and
each catalog binding points to a qualified authoritative G1 runtime without duplicating it.
