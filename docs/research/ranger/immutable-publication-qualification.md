# Ranger R0.2 Immutable-Publication Qualification Evidence

**Status:** provider-neutral evidence contract and deterministic simulation path; no live backend
is qualified

**Schema:** `ets.ranger.immutable-publication-qualification.v1`

**Tracks:** #605

## Objective

Define the evidence a third party needs to evaluate one bounded object-retention trial without
inferring immutability from a provider name, an SDK success response, or a SQLite setting. The
profile binds one exact Ranger publication archive bundle and expected publication head to:

1. backend configuration evidence;
2. the retention put response;
3. evidence that the deletion probe principal had delete capability;
4. a retention-enforced deletion denial; and
5. retrieval of the same object version and content after that denial.

All five raw artifacts are required at verification time. Their SHA-256 digests are included in
an evidence-issuer-signed qualification record. The verifier independently recomputes those
digests; an opaque digest without its artifact is insufficient.

## Evidence composition

`verify_immutable_publication_qualification` verifies the following boundaries in order:

- the verifier-pinned qualification, publication scope, backend instance/namespace, object key and
  version, deletion-probe principal, execution environment, fresh challenge nonce, evidence
  issuer, and signing-key identities;
- the evidence issuer signature and the five raw artifact digests;
- the complete external-publication chain through a separately supplied expected head;
- historical publisher-key standing for every receipt under the supplied authority history;
- the canonical digest of the ordered archive bundle;
- the custodian-signed retrieval audit and its historical key standing;
- current custodian standing relative to the full authority history presented to this verifier;
- the audit's exact expected-head match and receipt count;
- reported versioning, compliance-mode retention, no configured retention bypass, and the minimum
  verifier policy duration;
- a reported delete denial by retention; and
- a reported post-denial retrieval of the exact retained bundle.

The expected publication head, authority history, public keys, backend identity, object key and
version, deletion-probe principal, evidence environment, and minimum retention duration come from
verifier policy. They are never discovered from the qualification record.

## Simulation and live adapters

A simulator and a future live adapter emit the same versioned source record and preserve the same
five artifact classes. A record labeled `simulation` may be valid and profile-conformant, but the
verifier always reports `simulation_profile_only=true` and
`provider_control_plane_evidence_profile_passed=false`.

A record labeled `provider_control_plane` can pass only the bounded provider-evidence profile. It
means the configured evidence issuer signed a conformant account of the supplied artifacts. It
does not prove that the provider generated those bytes, that an independent organization operated
the issuer, that all deletion paths were unavailable, or that physical media is WORM. A
provider-specific artifact verifier and a controlled live qualification run are required before a
deployment decision.

## Source record

The signed record includes:

- qualification, verifier-challenge, publication-scope, backend-instance, namespace, object-key,
  and object-version identities;
- the exact expected and retained publication-head digests;
- a canonical digest over the ordered full publication archive bundle;
- the exact custodian retrieval-audit digest;
- five distinct content-addressed evidence-artifact digests;
- configuration, put, deletion-attempt, retrieval, and reported retention-until times;
- retention mode, versioning state, and whether a bypass is reported;
- deletion-probe identity, outcome, and bounded result detail;
- retrieval outcome and observed archive-bundle digest;
- evidence issuer identity, signing-key identity, fingerprint, digest, and Ed25519 signature; and
- explicit false claim flags for evidence-issuer key lifecycle, physical WORM storage,
  organizational independence, hardware rollback resistance, trusted time, global currentness,
  continued availability, operational authorization, complete capture, semantic truth, actuator
  response, and physical outcome.

The reported timestamps are ordered and useful for reconstruction, but the record does not attach
trusted-time evidence. The reported retention interval therefore remains a signed assertion by the
configured evidence issuer.

## Threat model

| Threat / attack surface | Impact | Implemented mitigation and detection | Missing deployment mitigation | Test strategy |
| --- | --- | --- | --- | --- |
| Backend or namespace substitution | Evidence from another storage boundary is accepted | Verifier-pinned provider, instance, namespace, object key/version, and signed record | Provider-native resource identity attestation | Substitute backend policy identity |
| Stale or forked publication head | Later Ranger evidence disappears | Exact expected head, full chain, predecessor, sequence, standing, and canonical bundle verification | Independently refreshed/quorum head observations | Present a valid stale prefix and reordered chain |
| Publisher/custodian key substitution or revocation | Forged receipt or audit is accepted | Authority-relative source-key standing; retrieval custodian must also be current relative to presented history | Trusted source-signature time and globally current authority view | Revoke custodian after historical standing |
| Fabricated configuration response | Retention is claimed without enforcement | Raw artifact required, content digest verified, configured issuer signature | Provider-specific signed/API evidence parser and independent capture | Mutate raw configuration artifact |
| Delete test uses an incapable or substituted principal | Denial is meaningless | Separate delete-capability artifact and verifier-pinned probe identity are required | Provider authorization-graph verification at trial time | Omit capability artifact or substitute probe policy identity |
| Deletion succeeds or bypass is enabled | Retained history can be erased | Compliance mode, versioning, no reported bypass, and deletion-denial requirements | Enumerate privileged and lifecycle deletion paths in live run | Sign a successful-delete trial |
| Object/version substitution after denial | Retrieval does not demonstrate retained bytes | Exact object version, archive-bundle digest, and post-denial content match | Provider-native version/retention attestation | Alter retrieval artifact or bundle digest |
| Evidence artifact deletion/modification | Trial cannot be independently reconstructed | All five non-empty content-distinct artifacts are required and hash-bound | Separate immutable evidence-package custody | Remove or modify an artifact |
| Simulation mislabeled as live | Synthetic evidence is treated as deployment evidence | Execution environment is signed and separately pinned by verifier policy | Protected live-run identity and provider-specific artifact verification | Verify simulation cannot pass provider profile |
| Qualification replay | Old configuration and trial results appear current | Fresh verifier challenge is signed and separately pinned | Durable challenge/qualification registry and trusted time | Substitute a prior challenge nonce |
| Clock manipulation | False retention-window claim | Ordered aware timestamps and explicit `trusted_time_proven=false` | Trusted-time attestations over configuration and operation artifacts | Preserve false time claim in successful result |

## Claim boundary

A successful simulation verification establishes schema conformance, signature and artifact
integrity, exact publication/custodian lineage, and internally consistent trial semantics. It does
not establish a live backend property.

A successful provider-control-plane result additionally establishes that the configured evidence
issuer signed the reported control-plane trial over the supplied artifacts. It still does **not**
establish physical WORM media, organizational independence, hardware rollback resistance, trusted
time, global latest-state currentness, continued availability, operational/Fleet authorization,
complete capture, semantic truth, actuator response, or physical outcome.

ETS Core retains canonicalization/hash/proof ownership. Gateway remains out of the real-time
safety loop. This profile changes no motion, actuator, watchdog, E-stop, or authorization behavior.

## Differentiation and IP note

A possible differentiation hypothesis is the exact verifier composition of authority-relative
publisher/custodian standing, an independently supplied publication head, raw object-retention
control-plane artifacts, a capability-qualified deletion-negative trial, post-denial content
retrieval, and machine-readable nonclaims. No novelty or patentability conclusion has been made,
no closest prior art was established in this slice, and any claim drafting requires a dedicated
prior-art search and counsel review.

## Deployment qualification still required

No provider, hardware, or cloud account is selected or purchased by this slice. Before a live
trial, compare a local compatible emulator, one managed object-lock service, and a separately
administered replicated option for policy semantics, API compatibility, region/account separation,
retention escape paths, evidence export, availability, and cost. The cheapest first experiment is
the deterministic simulator and mutation suite in ordinary CI.

The next live slice should implement one provider-specific artifact parser and run the contract in
a protected, non-production qualification namespace. Only produced evidence may advance the
corresponding bounded provider claim.
