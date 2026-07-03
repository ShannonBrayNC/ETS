# Durable artifact registry

ETS artifact registration stores artifact metadata and hashes in the transparency log. Raw artifact bytes are not stored.

`ets.core.artifact_registry.load_artifact_registry()` rebuilds the in-memory artifact registry from persisted log entries. This allows SQLite-backed deployments to reconstruct artifact records after restart from the durable event log.

## Stored fields

The reconstructed registry uses:

- artifact id
- artifact hash
- reference URI
- content type
- byte size
- JSON metadata
- ingestion timestamp
- event id
- log index

The original base64 body or raw artifact bytes are intentionally excluded.

## Failure behavior

Corrupt artifact metadata fails closed by raising `ArtifactRegistryError`. Duplicate artifact ids in the persisted log also fail closed.

## API wiring

The reconstruction helper is ready for API startup integration. The remaining app wiring should initialize `app.state.artifact_records` from `load_artifact_registry(event_log.list_entries())` when a durable store is used.
