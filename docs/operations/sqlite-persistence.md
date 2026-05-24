# SQLite Persistence and Migration Notes

SQLite is the durable local storage provider for ETS `v0.1.0-alpha` validation and demos.

It is intended for:

- local development
- deterministic smoke testing
- small controlled demos
- restart/persistence validation

It is not the final hosted storage design.

## Enable SQLite mode

```powershell
$env:ETS_STORAGE_PROVIDER = "sqlite"
$env:ETS_SQLITE_PATH = ".data\ets.db"
.\.venv\Scripts\python.exe -m uvicorn ets.api.app:app --reload --port 8000
```

The API readiness endpoint should report:

```json
{
  "storage": "sqlite"
}
```

## Durability expectations

SQLite mode should preserve:

- appended event metadata
- event hash
- leaf hash
- monotonic log index
- duplicate event rejection
- event list order
- read-by-ID behavior
- read-by-index behavior
- inclusion proof generation after process restart

## Schema version

The current SQLite store reports schema version `1`.

Before changing the schema:

1. add a migration note to this document
2. add or update a schema-version test
3. keep existing v0.1 fixture behavior readable where practical
4. document compatibility impact in release notes

## Migration policy for alpha

During alpha, destructive schema changes are allowed only if they are explicit and documented. A schema change must not silently reinterpret existing event hashes or log indexes.

If a migration is needed, prefer:

- additive columns
- explicit schema version increments
- idempotent migration code
- tests that open an older database and verify expected behavior

## Hosted roadmap

PostgreSQL or another hosted event-store provider should be added only after:

- protocol test vectors are stable
- verifier golden tests are stable
- tenant/workspace scoping behavior is stable
- append-only semantics are tested across restarts and concurrent writes

## Related tests

SQLite behavior is covered by:

- `tests/unit/test_sqlite_event_store.py`
- `tests/integration/test_api_security_persistence.py`

These tests should remain local and deterministic. They should use temporary database paths, not a fixed `.data` folder.
