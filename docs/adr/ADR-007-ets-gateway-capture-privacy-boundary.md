# ADR-007: ETS Gateway Applies Privacy Policy Before Immutable Commitment and Binds Digests to Declared Representations

Status: Proposed for independent approval
Date: 2026-08-13
Parent: #215
Related research: SignalForge ETS-RI-08 / privacy-preserving evidence architecture

## Context

Enterprise telemetry can contain PII, PHI, credentials, secrets and other material that should not become permanently committed or broadly disclosed. Existing ETS Edge work establishes a capture envelope and default raw-content boundary, while newer Evidence Architecture research requires minimization before immutable commitment.

A digest is not encryption. Hashing low-entropy sensitive values can permit confirmation/dictionary attacks. The architecture therefore needs to state exactly what representation was hashed and avoid implying that a transformed/minimized digest represents original source bytes.

## Decision

1. Resource validation, source authorization, classification and capture/privacy policy execute before the canonical ETS commitment.
2. Prohibited fields are minimized/tokenized/redacted before the committed representation is canonicalized/hashed.
3. `content_digest` identifies the explicitly declared committed evidence representation.
4. If the source was transformed, transformation profile and lossless/lossy status are preserved.
5. The Gateway must not claim that the digest covers original source bytes unless the original-byte representation was actually authorized and committed.
6. Raw source content is not retained by default by ETS Gateway.
7. A future managed content store requires a separate governed profile for encryption, access, retention, deletion, jurisdiction and custody.
8. Adapters cannot bypass policy by directly mutating Core/Merkle storage.

## Consequences

- Privacy policy can intentionally trade exact-byte commitment for a minimized representation without lying about what was verified.
- A source-byte exact-hash profile remains possible when policy explicitly permits it.
- Transformation provenance becomes mandatory for normalized/minimized evidence.
- Gateway documentation and UI must distinguish source observation from derived representation.

## Validation

G1 tests must prove prohibited fields never enter committed metadata under the configured profile and that digest/transform labels match the actual representation.
