# ETS Research Paper RC2 Advanced Notes

ETS models an evidence transparency system as an append-only log over canonical
metadata records. The protocol uses SHA-256 for event and Merkle hashing,
Ed25519 for optional tree-head signatures, and offline verifiers for event hash,
inclusion proof, consistency proof, and proof bundle validation.

The RC5 lab uses simplified linear consistency proofs for the current
duplicate-last Merkle tree. This is intentionally explicit: it validates
extension against supplied leaf hashes but is not a compact Certificate
Transparency-style consistency proof.
