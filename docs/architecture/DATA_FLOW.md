# ETS Data Flow

1. A client submits an `EvidenceEvent` containing identifiers, metadata, and a
   content hash.
2. The API applies the configured redaction profile before hashing or storage.
3. The event is canonicalized and hashed through `ets.core`.
4. The append-only event store assigns a monotonic log index.
5. Leaf hashes are assembled into the Merkle tree root.
6. Clients fetch tree heads, inclusion proofs, proof bundles, or certificates.
7. Verification can run through the API or offline CLI/SDK.

Raw evidence bytes remain outside ETS unless a future profile explicitly adds
separate encrypted content storage.
