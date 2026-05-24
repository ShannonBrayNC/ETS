# ETS v0.1 Protocol Test Vectors

These vectors are frozen conformance examples for the `v0.1.0-alpha` line.

They are intentionally small, deterministic, and fictional. They are safe for repository use and must not be replaced with customer evidence or personal data.

## Files

- `event-vectors.json` covers canonical JSON serialization, event hashing, leaf hashing, and one tamper case.
- `../merkle-vectors.json` covers empty, single-leaf, two-leaf, three-leaf, and four-leaf Merkle roots.

## Canonical JSON rules

ETS v0.1 canonical JSON uses:

- UTF-8 encoding
- sorted object keys
- no insignificant whitespace
- JSON-native values only
- no non-finite numbers

## Regeneration policy

Do not regenerate these vectors as part of routine cleanup. A change to these files means the v0.1 compatibility contract changed.

If vectors must change intentionally:

1. Update the protocol documentation.
2. Update this README with the reason.
3. Update tests in `tests/spec/test_vectors.py`.
4. Call out the compatibility impact in release notes.
