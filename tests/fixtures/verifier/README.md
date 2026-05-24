# Verifier Golden Fixtures

This folder is reserved for deterministic verifier fixtures used by tests and demos.

The current golden verifier path is generated in-memory by `tests/unit/test_verifier_golden.py` so it cannot drift from the active model contracts. Future static fixtures may be added here when the v0.1 protocol vectors are fully frozen.

Golden verifier coverage must prove both sides of the trust gate:

- valid proof bundles verify successfully offline
- tampered proof bundles fail with a non-zero CLI result or invalid verification result
- generated JSON, Markdown, and HTML certificates contain the expected evidence identifiers and proof status

All fixture content must be fictional and small.
