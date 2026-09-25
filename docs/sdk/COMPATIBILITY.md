# SDK compatibility and versioning

The ETS package version is not the protocol version.

SDK-1 freezes the following compatibility declaration:

- Application SDK: `ets.application.sdk.v1`
- REST API: `v1`
- Evidence event: `ets.event.v1`
- Capture envelope: `ets.capture.v1`
- Proof bundle: `ets.proof_bundle.v1`
- Verifier contract: `ets.verifier.v1`
- Connector SDK: `ets.connector.sdk.v1`

Python exposes the same declaration as
`APPLICATION_SDK_COMPATIBILITY_V1`.

## Rules

1. Package patch/minor versions may evolve without changing a protocol contract
   when behavior remains compatible.
2. A backward-incompatible wire/model/semantic change requires a new explicit
   contract identifier.
3. Language SDKs must advertise the exact protocol contracts they support.
4. Unsupported contract versions fail explicitly; they must not be silently
   reinterpreted.
5. Client-side hash/proof implementations require conformance vectors. Transport
   wrappers may be generated from OpenAPI, but generated route names are not the
   stable ergonomic SDK API.
