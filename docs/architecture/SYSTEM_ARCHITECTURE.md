# ETS System Architecture

ETS uses one canonical protocol core. API, CLI, SDK, reports, Explorer, demos,
and experiments must call `ets.core` instead of duplicating hashing, Merkle, or
proof logic.

```text
Explorer / CLI / SDK / Reports
              |
              v
        FastAPI service
              |
              v
     ets.core protocol library
              |
              v
  EventStore: memory or SQLite
```

The RC implementation is a local reference stack. Hosted deployment needs a
separate production auth, rate limiting, signing, persistence, and operations
review before it can be called a trust service.
