# ETS Storage Model

The active storage contract is `ets.core.storage.EventStore`.

RC providers:

- `InMemoryAppendOnlyLog` for tests and ephemeral local development.
- `SQLiteEventStore` for durable local validation and demos.

Stored records include canonical event JSON, event hash, leaf hash, append index,
and created timestamp. ETS does not store raw evidence bytes in the RC storage
model.

Future hosted providers should preserve the same contract and add tenant-aware
indexes, backups, migrations, and operational monitoring.
