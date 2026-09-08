# Ranger R0.2 Authority-Bound Retained Checkpoints

**Status:** executable software-reference contract; freshness and key standing are
registry-relative

**Profiles:** `ets.ranger.retained-key-authority-head.v1`,
`ets.ranger.authority-bound-retained-checkpoint.v1`

**Tracks:** #605

## Objective

Bind each verifier-accepted Ranger custody head to the exact custody-key authority history used
to validate it. This closes two independent replay gaps without treating either signature
validity or a locally supplied history as self-proving standing:

1. a valid Ranger custody chain may have been signed by a superseded, revoked, or substituted
   key; and
2. a valid authority-history prefix may itself be stale relative to history already retained by
   the verifier.

The profile composes, rather than replaces, the existing custody, key-authority, and retained
checkpoint contracts. The original `ets.ranger.retained-checkpoint.v1` remains a static-key R0.2
profile. The composed profile is a new versioned source structure so existing consumers do not
silently acquire different standing semantics.

## Evidence flow and trust boundaries

```text
authority-signed key events
        │ complete history
        ▼
verify authority chain ──► retain and registry-sign authority head
                                      │ exact retained view
Ranger custody chain ──► resolve boot key ──► verify custody and continuity
                                      │
                                      ▼
                   registry-sign authority-bound custody checkpoint
```

The two retained chains use the same configured verifier-registry identity in this software
reference but have separate schemas and SQLite stores:

- `RangerAuthorityHeadRegistry` verifies the complete authority history and retains its event
  count and head digest in an append-only registry-signed chain.
- `RangerAuthorityCheckpointRegistry` resolves the Ranger key for the presented boot from that
  history, verifies the complete Ranger custody chain, and binds the accepted custody head to the
  exact retained authority-head checkpoint.

An independent verifier therefore needs the complete Ranger custody chain, the authority-bound
checkpoint chain, the retained authority-head chain, the complete authority-event history, and
the expected authority and registry public keys. A checkpoint alone cannot reconstruct source
custody or prove that its authority view is the latest view held elsewhere.

## Authority-head retention contract

`RangerAuthorityHeadRegistry.retain`:

1. validates the complete `ets.ranger.key-authority-event.v1` history, including canonical
   digests, authority signatures, possession proofs, transitions, identity, and scope;
2. rejects an event-count rollback, an equal-count fork, or a longer history that does not
   contain the retained head at the retained position;
3. treats an exact repeat as idempotent;
4. binds the vehicle, tenant, workspace, authority identity and key fingerprint, registry
   identity and key fingerprint, event count, authority head digest, receipt time, and prior
   retained-head checkpoint; and
5. appends a registry-signed `ets.ranger.retained-key-authority-head.v1` record.

The first record is explicitly a registry baseline. Later records prove only extension relative
to that retained baseline. `verify_presented_history` distinguishes a stale prefix, an equal-size
fork, and a history ahead of the supplied retained view; none of those conditions is reported as
global currentness.

## Authority-bound custody acceptance

For each submission, `RangerAuthorityCheckpointRegistry.retain` performs these operations in
order:

1. durably retain or recover the verified authority-history head;
2. require a complete Ranger custody chain beginning with
   `ets.ranger.boot-checkpoint.v1`;
3. resolve the expected custody public key and historical standing for that boot sequence;
4. reject a credential that is unknown, not yet active, superseded, revoked, or mismatched;
5. verify the complete custody chain under the resolved public key;
6. compare the Ranger head and authority head with the latest composed checkpoint;
7. enforce same-boot prefix extension or exact adjacent-boot binding; and
8. append a registry-signed `ets.ranger.authority-bound-retained-checkpoint.v1` record.

The resulting checkpoint binds:

- vehicle, tenant, workspace, mission, boot identity, and boot sequence;
- Ranger custody record count and head digest;
- Ranger signing-key identifier and fingerprint;
- previous boot and previous custody head where applicable;
- retained authority-head registry sequence and signed checkpoint digest;
- authority event count and history head digest;
- authority and registry identities and key fingerprints;
- verifier receipt time and explicit Ranger/authority advancement flags; and
- explicit negative claims for global currentness, operational authorization, trusted time,
  completeness, semantic truth, and physical outcome.

An exact repeat is idempotent. A later checkpoint may advance Ranger state only, authority state
only, or both. Authority-only advancement is important: a verifier can preserve a new rotation or
revocation while the physical machine remains at the same accepted custody head.

## Revocation precedence and split-store recovery

Authority-head retention deliberately occurs before custody acceptance. If newly retained
authority history revokes the key used by a correctly signed new Ranger boot, the authority head
is committed and the custody submission fails. A subsequent replay of the older authority prefix
is then rejected as stale.

The two SQLite appends are not one cross-database atomic transaction. A crash after authority-head
retention and before custody-checkpoint retention can leave authority state ahead of composed
custody state. Recovery accepts that safe asymmetry: retrying the full input is idempotent and may
create the missing composed checkpoint, while no custody state is accepted before its authority
view. A new composed checkpoint cannot claim a receipt time earlier than its bound authority head.

This is a software-reference fail-closed ordering rule, not a claim of distributed transaction
atomicity. Production deployment still needs transactional service boundaries, replicated
immutable publication, reconciliation evidence, and rollback-resistant latest-head storage.

## Independent verification surfaces

Three verification levels keep their propositions separate:

- `verify_checkpoint_chain` checks strict schemas, canonical digests, registry signatures,
  identity stability, predecessor linkage, and declared Ranger/authority advancement. It reports
  `authority_bindings_verified=false` because checkpoint records alone are insufficient.
- `verify_bound_checkpoint_chain` additionally verifies the retained authority-head chain,
  matches the latest complete authority history, reconstructs every referenced history prefix,
  and evaluates the Ranger key at each checkpoint's boot sequence.
- `verify_presented_chain` requires the retained authority-head chain, current complete authority
  history, and presented Ranger custody chain. It verifies the exact referenced authority head,
  current authority-relative key standing, Ranger signatures, and equality with the supplied
  latest composed checkpoint.

Historical evidence is not retroactively destroyed by a later effective rotation or revocation.
A boot before the declared boundary can retain historical standing; a boot at or after the
boundary must use the then-authorized key.

## Architecture boundaries and claim limits

- **ETS Core** remains authoritative for canonicalization, digest, and proof semantics. These
  profiles use Core canonical JSON but do not introduce a new Core inclusion proof.
- **ETS Fleet** remains the operational enrollment and authorization plane. Authority-relative
  key standing does not grant network, mission, module, policy, or motion authority.
- **ETS Verifier** is the natural deployment boundary for retained heads and composed
  verification. This reference does not prove that the process is administratively or physically
  independent from Ranger.
- **ETS Edge and Black Box** may preserve and transport source chains and receipts, but possession
  of a copy does not establish latest-state standing.
- **ETS Gateway** may transport submissions but stays outside Ranger's real-time safety loop and
  cannot be required for braking, E-stop, watchdog, or loss-of-command behavior.
- **AI Witness** may add separately attributable observations. It cannot upgrade key standing,
  integrity, inclusion, or an actuator response into semantic truth or physical outcome.
- **Evidence Objects** may reference these records as source evidence. Inclusion, standing,
  consequence custody, authorization, semantic truth, actuator response, and observed outcome
  remain separate findings.

## Threat coverage

| Threat | Attack surface | Impact | Current mitigation / detection | Missing mitigation | Required evidence | Test strategy |
| --- | --- | --- | --- | --- | --- | --- |
| Stale valid authority prefix | Export, verifier input, restored authority database | Revocation or rotation is hidden | Separately retained event count/head; reject rollback, fork, and non-prefix extension | Multi-party publication and rollback-resistant counters | Full authority history, retained authority-head chain, expected keys | Replay shorter, equal-count forked, and longer non-prefix histories |
| Correct signature from revoked or superseded Ranger key | Vehicle runtime or replayed custody | Unauthorized key is mistaken for current Ranger identity | Resolve key standing at the declared boot before accepting custody | Hardware key destruction and live Fleet/provider revocation | Authority history, retained heads, complete custody, boot sequence | Submit correctly signed post-revocation boot and preserve pre-boundary history |
| Unauthorized rotation or key substitution | Key-binding request and boot transition | Attacker key gains apparent continuity | Old/new possession proofs, authority signature, exact boot-boundary resolution, stable scope | Authenticated administration, quorum recovery, hardware attestation | Signed intents, both possession proofs, authority chain, adjacent boot chains | Wrong proof, unregistered key, same-boot change, and alternate key tests |
| Authority-history deletion after failed custody | Split persistence or operator recovery | Rejected revocation is forgotten and old history replayed | Authority head commits before custody acceptance; stale prefix then fails | Cross-service transaction/reconciliation and immutable replication | Both stores, failed-submission receipt/audit, retained head | Retain revocation, reject custody, then replay earlier history |
| Ranger custody truncation or fork | Vehicle storage, export, or compromised signer | Previously accepted records disappear or diverge | Retained record position/head and same-boot prefix check | Hardware-backed signer and registry gossip | Full chain and latest composed checkpoint | Submit shorter, equal-count alternate, and longer non-prefix chains |
| Skipped or substituted boot | Boot counter and boot-checkpoint construction | Restart or custody gap is concealed | Exact adjacent sequence and signed previous-boot/head binding | Hardware anti-rollback boot counter and measured boot | Current and previous custody heads, boot checkpoints, authority history | Submit a sequence gap or substituted predecessor |
| Cross-device, mission, tenant, or workspace confusion | Registry configuration and verifier input | Valid evidence is attributed to the wrong scope | Stable signed scope in authority heads and composed checkpoints; configured expected identities | Fleet-authoritative composition | All signed chains plus expected tenant/workspace/mission | Substitute identity or mix chains between registries |
| Registry database modification or stale writer | SQLite files and concurrent processes | Signed state is hidden, reordered, or indexed deceptively | WAL/FULL, atomic per-store predecessor check, strict recovery, signed/index comparison | WORM/immutable replication, quorum heads, backup provenance | Database, signed chains, separately witnessed latest heads | Modify unsigned indexes, signatures, order, and append from stale instance |
| Registry or authority signer compromise | Software keys and verifier/authority runtimes | Fabricated heads or lifecycle events verify cryptographically | Purpose-separated expected keys and explicit software-key classification | HSM/TPM, key lifecycle, attestation, separation of duties, incident evidence | Key histories, attestations, service audit logs | Wrong-key and tampered-signature controls; hardware tests deferred |
| Clock manipulation | Authority event time or verifier receipt input | Misleading chronology | Security transitions use signed boot sequence; receipt ordering is monotonic and separately labeled | Authenticated witnessed time and bounded uncertainty validation | Raw time sources, clock quality, receipt evidence, boot counter | Naive/retrograde receipt rejection and manipulated-time scenarios |

## Storage and cost limits

Both SQLite stores use WAL mode, `synchronous=FULL`, append-only logical sequences, signed
predecessor linkage, and unsigned-index-to-signed-record recovery checks. Keys are software-held;
data is not encrypted, replicated, write-once, or hardware-attested. The implementation is
hardware-independent and adds no R0 procurement cost.

## Differentiation hypothesis and IP uncertainty

The composition of separately retained key-authority heads with boot-scoped physical-machine
custody checkpoints, including authority-first revocation persistence and exact historical
authority-view binding, may be differentiating. No prior-art search was performed for this
increment. Novelty and patentability are unknown and require a dedicated search and counsel
review.
