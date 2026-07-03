# ETS Storage Model

The active storage contract is `ets.core.storage.EventStore` for append-only transparency events. SQLite mode also persists artifact registry metadata through `SQLiteEventStore` artifact helpers.

RC providers:

- `InMemoryAppendOnlyLog` for tests and ephemeral local development.
- `SQLiteEventStore` for durable local validation and demos.

Stored event records include canonical event JSON, event hash, leaf hash, append index, and created timestamp.

Stored artifact registry records include artifact ID, artifact hash, reference URI, content type, byte size, JSON metadata, ingestion timestamp, event ID, and log index. The SQLite artifact table intentionally excludes uploaded artifact payload fields such as base64 content; ETS stores hashes and metadata only.

SQLite artifact metadata reads fail closed. Invalid JSON metadata, invalid timestamps, invalid hashes, negative byte sizes, or malformed records raise `StorageValidationError` instead of returning untrusted metadata.

Future hosted providers should preserve the same contract and add tenant-aware indexes, backups, migrations, and operational monitoring.
