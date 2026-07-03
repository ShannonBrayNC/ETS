# Artifact route wiring acceptance checklist

This checklist tracks the remaining ETS-002 API wiring work for the durable artifact registry.

## Current state

- `ets.core.artifact_registry.load_artifact_registry()` can rebuild artifact records from persisted log entries.
- `ets.api.app.create_app()` still initializes `app.state.artifact_records` as an empty in-memory dictionary.
- `/evidence/register`, `/evidence/{artifact_id}`, `/evidence/{artifact_id}/proof`, and `/evidence/verify` depend on `app.state.artifact_records`.

## Required implementation

1. Initialize `app.state.artifact_records` from `load_artifact_registry(event_log.list_entries())` during app startup.
2. Fail closed if persisted artifact metadata cannot be reconstructed.
3. Keep in-memory local/demo behavior for logs that do not persist across process restarts.
4. Ensure duplicate checks use the reconstructed registry before appending new artifact events.
5. Ensure registration updates the active registry after a successful append.

## Required tests

Add an integration test using `TestClient(create_app(log=SQLiteEventStore(path)))` that:

1. Registers an artifact.
2. Recreates the app with a new `SQLiteEventStore(path)` instance.
3. Reads the artifact through `/evidence/{artifact_id}`.
4. Fetches `/evidence/{artifact_id}/proof`.
5. Verifies the artifact through `/evidence/verify`.
6. Attempts duplicate registration and receives a conflict.
7. Confirms no raw artifact payload field is persisted.

## Completion gate

Do not mark ETS-002 complete in SignalForge until the implementation and integration tests above are merged with green CI and code-scanning status is either verified or explicitly documented as unavailable.
