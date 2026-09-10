# Ranger R0.2 Publication and Custodian Key Lifecycle

**Status:** authority-relative, software-reference lifecycle profile; no hardware-backed key or
trusted-time deployment is implied

**Schemas:** `ets.ranger.publication-key-binding-intent.v1`,
`ets.ranger.publication-key-binding-request.v1`,
`ets.ranger.publication-key-authority-event.v1`, and
`ets.ranger.publication-source-key-standing.v1`

**Tracks:** #605

## Objective

Allow a verifier to distinguish three propositions that a bare source signature cannot safely
collapse:

1. a particular publisher or custodian key signed a particular source record;
2. that key had authority-relative standing in one exact retained lifecycle-history prefix; and
3. that same key is or is not currently active relative to the larger lifecycle history presented
   to the verifier.

This lets historical publication receipts and retrieval audits remain independently verifiable
after key rotation or revocation. It deliberately avoids the unsafe conclusion that an old key is
currently authorized just because an older record verifies with it.

The profile covers the two separately keyed roles introduced by the publication archive:

- `publisher` signs `ets.ranger.external-publication-receipt.v1`; and
- `custodian` signs `ets.ranger.publication-retrieval-audit.v1`.

The profile does not change the receipt, audit, ETS Core canonicalization, Fleet authorization,
Gateway, motion controller, actuator behavior, or real-time safety loop.

## Lifecycle evidence

Each configured publication scope has one authority-signed, append-only event history. The scope
uses the `ets-ranger-publication:` namespace and pins the publisher principal, custodian
principal, authority identity, authority signing-key identity, and authority public-key
fingerprint.

For either role, the valid transition sequence is:

1. `enroll` — requires proof of possession from the proposed role key;
2. `rotate` — requires possession proofs from both the active old key and the replacement key;
3. `revoke` — is an authority decision with a bounded revocation reason and is terminal for that
   role in this scope.

The lifecycle rejects a non-enrollment first event, duplicate request IDs, reordered or forked
sequences, predecessor mismatches, role/principal changes, reused key IDs, reused public keys,
cross-role key reuse, use of the authority key as a source key, invalid proofs, a wrong active
transition subject, and transitions after revocation. The SQLite reference adapter uses WAL,
`synchronous=FULL`, transactional append checks, strict parsing, unique index constraints, and
index-to-signed-record comparison. These are logical append controls, not evidence of physical
immutability.

## Source-key standing and verification

`RangerPublicationKeyAuthorityLedger.attest_source_key_standing` signs a
`ets.ranger.publication-source-key-standing.v1` record. It binds:

- one exact source digest;
- source kind, principal, role, signing-key ID, and public-key fingerprint;
- the exact authority-event count and authority-history head digest; and
- the authority event sequence that made that key active in the named prefix.

`verify_publication_source_key_standing` independently validates the full presented authority
history, the signed standing record, the exact named prefix, the source identity binding, and the
source signature using the historically standing key. It reports
`currently_authorized_relative_to_presented_history` separately. A later rotation or revocation
therefore makes an old key non-current while preserving a valid historical standing result.

The verifier makes no claim that the source record was signed *while* the named prefix was current.
The receipt/audit timestamps are not trusted time, and the lifecycle event timestamp is also an
untrusted source field. That temporal assertion requires a separately configured trusted-time
binding over the relevant source and lifecycle evidence.

`verify_publication_lifecycle_chain` adds mixed-key publication-chain verification. It preserves
the normal contiguous-sequence, predecessor, duplicate-binding, registry-identity, and expected-
head checks, while resolving each receipt with its own historical publisher standing. A mixed-key
chain can be valid even when an earlier key is no longer current in the presented history.

## Threat model

| Threat / attack surface | Impact | Current mitigation and detection | Missing production mitigation | Test strategy |
| --- | --- | --- | --- | --- |
| Publisher/custodian key compromise | Forged future source records | Authority revocation makes the key non-current; historical result remains explicit | Hardware-backed keys, attestation, protected administration, incident workflow | Revoke an audit key and verify historical-but-not-current standing |
| Silent key substitution | A record is attributed to a different signer | Source key ID, fingerprint, public-key validation, source signature, and standing binding must all match | Hardware enrollment ceremony and key provenance | Substitute source/standing key fields or signatures |
| Rotation without old/new control | Unauthorized takeover or unusable replacement | Rotation requires both active-old and replacement possession proofs | Multi-party approval and external policy evidence | Invalid old/new proof test |
| Cross-role key reuse | Publisher and archive custody collapse into one key | Global key-ID and public-key reuse rejection across roles | Independent organizations and infrastructure | Attempt custodian enrollment with publisher key |
| Lifecycle deletion, fork, reordering, or stale prefix | A verifier accepts a manipulated authority view | Signed contiguous chain, predecessor links, request uniqueness, explicit named prefix/head | Independently retained authority heads, WORM replication, quorum publication | Reordered history and mismatched standing-head tests |
| Misread old key as current | Historical record grants present authority | Separate historical-standing and current-relative fields | Authenticated current authority service / signed latest-head observations | Rotate a publisher key and assert old record remains non-current |
| Timestamp manipulation | False claim that a signature preceded revocation | `source_signature_time_proven` and `trusted_time_proven` remain false | Trusted-time attestations bound to source and lifecycle digests | Verify output claim flags and reason boundary |
| Privileged SQLite modification | Lifecycle events or indexes change | SQLite integrity check plus signed record/index comparison | WORM/object-lock and protected administration | Direct lifecycle-index mutation test |

## Claim boundary

When verification succeeds, this profile establishes only:

- validity of the configured authority signature and append-only lifecycle evidence presented;
- possession-proof-checked enrollment/rotation transitions and bounded authority revocation;
- a source signature by the key that stood in the exact named authority-history prefix; and
- whether that key matches the active key relative to the full history supplied to the verifier.

It does **not** establish global lifecycle currentness, source-signature time, trusted time,
hardware-backed identity, operational/Fleet authorization, physical WORM storage, continued
custody or availability, organizational independence, complete capture, semantic truth, actuator
response, or physical outcome.

## Deployment adapter contract

A production authority adapter may preserve these source schemas and verifier semantics, but must
emit independently verifiable evidence for stronger claims. That evidence should include key
attestation, authorization and approval policy, administrative identity and separation, immutable
event publication, retained latest-head observations, revocation handling, trusted-time evidence,
retrieval/availability observations, and deletion-negative tests. A provider name, a successful
API request, or a software database setting is not enough to make those claims.

## Next sequential slice

Qualify a separately administered immutable publication backend (for example an object-lock/WORM
adapter) with retained latest-head custody, backend configuration evidence, publisher/custodian
key-lifecycle composition, retrieval auditing, and deletion-negative tests. Do not label a backend
immutable or independent until the produced evidence supports those claims.
