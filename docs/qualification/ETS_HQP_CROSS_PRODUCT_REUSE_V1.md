# ETS HQP Cross-Product Reuse v1

**Tracking:** #797  
**Status:** Repository-side HQP-4 contract  
**Products:** Provenance / ETS Mobile Android Phase 1A; legacy network/syslog hardware lab

## Purpose

HQP-4 demonstrates that ETS hardware qualification is a shared evidence methodology rather than a collection of product-specific test frameworks.

The products may require different physical tests, device facts, safety controls, and resulting-state assertions. They may not weaken the common HQP evidence chain:

```text
device-under-test
→ qualification environment
→ test profile
→ immutable build identity
→ observer identity
→ starting state
→ stimulus
→ observations
→ resulting state
→ Evidence Object(s)
→ independent HQP-2 verification
→ qualification report
```

The Android and legacy profiles therefore inherit `ets.hardware-qualification.v1`, emit HQP-1 run/report packages, and are independently checked by the same HQP-2 verifier.

## Portability invariant

Product-specific differences belong in profile test cases and source-to-HQP binding manifests. The following common semantics must remain equivalent across reuse profiles:

- all common HQP evidence classes;
- raw-artifact digest retention;
- Evidence Object binding;
- all HQP verifier checks;
- independent verification for `qualified` and `qualified_with_deviation`;
- no trust in the DUT runtime;
- the common disposition policy;
- separation of capability maturity from qualification state;
- no silent cross-revision qualification;
- requalification on claim-critical change;
- explicit supersession and immutable historical results.

`ets.qualification.reuse.common_hqp_semantics_fingerprint()` hashes only these common semantics. Android and legacy profiles must produce the same fingerprint even though their test inventories differ.

The fingerprint is a portability/conformance aid. It is not a qualification result.

## Android Phase 1A reuse

Profile:

`docs/qualification/profiles/ets-provenance-android-phase1a-hardware-qualification-v1.json`

Binding manifest:

`docs/qualification/reuse/android-phase1a-hqp-reuse-v1.json`

The source product contract is pinned to:

- repository: `Lantern-Protocol/ETS-Mobile`;
- path: `docs/ANDROID_PHASE1A_DEVICE_QUALIFICATION.md`;
- source revision: `fefba5069da1d33251211dd3d67d176bade478c2`;
- product gate: `Lantern-Protocol/ETS-Mobile#4`.

HQP-4 does not replace the Mobile Evidence Capture Boundary or its existing device qualification report. It binds that evidence into the common HQP package.

The Android specialization retains:

- exact CameraX output-byte commitment;
- `ETS_CAPTURED` versus `ETS_IMPORTED` origin classification;
- Android Keystore security-level reporting without capability inflation;
- APK signing-certificate binding;
- local Evidence Object/provenance commitment;
- cold-process journal recovery;
- bounded negative/failure evidence.

A hardware-backed or StrongBox-capable key does not establish semantic truth, causality, or complete observation.

## Legacy network/syslog reuse

Profile:

`docs/qualification/profiles/ets-legacy-network-syslog-hardware-qualification-v1.json`

Binding manifest:

`docs/qualification/reuse/legacy-network-syslog-hqp-reuse-v1.json`

The first legacy target class is:

`LEGACY-NET-SYSLOG-RT0`

It represents a named physical legacy network device that can emit RFC 5424 VERSION 1 UDP into the existing controlled ETS Edge syslog observer boundary.

The target class is not a hardware model and is not itself qualified. A physical run must replace it with exact manufacturer, model, hardware revision, firmware, configured syslog identity/transport, observer Edge build, interface, network path, and time-source facts.

The legacy specialization retains:

- exact received-datagram SHA-256 commitment before parsing;
- bounded parsed RFC 5424 metadata;
- source IP/port observations;
- Evidence Object/proof references;
- one-byte mutation distinction;
- observer restart recovery;
- source/network interruption boundaries.

UDP source IP/port and RFC 5424 hostname/app/procid/msgid fields are observations. They are not authenticated source identity. Missing observation during an interruption is not evidence that no source event occurred.

## Producer/verifier separation

A product runtime, qualification host, or lab adapter may collect and package HQP evidence. It may not make itself the independent authority for a `qualified` claim.

A physical Android or legacy execution should proceed as:

1. capture the exact source/product qualification evidence;
2. bind DUT/build/environment/observer identity;
3. retain stimuli, observations, resulting states, raw artifacts, and Evidence Objects;
4. seal the HQP-1 run/report;
5. move the retained package into an independent verification context;
6. execute HQP-2 against the canonical profile and retained bytes;
7. retain the HQP-2 verification result with the qualification report.

## Repository CI boundary

CI may prove that:

- both profiles parse under the common HQP schema/runtime;
- both manifests bind to their intended source contracts;
- neither profile weakens common evidence or verifier requirements;
- both profiles produce the same common-semantics fingerprint;
- deterministic summaries are stable.

CI does **not** qualify a physical Android device or a legacy hardware source.

## HQP-4 physical exit gate

Issue #797 remains open until both of the following exist:

1. one named physical Android device executes the Android Phase 1A profile, produces a retained HQP-1 package, and passes HQP-2 independent verification;
2. one named physical legacy network device executes the legacy syslog profile, produces a retained HQP-1 package, and passes the same HQP-2 independent verification machinery.

Only then does Wave 0 have direct physical evidence that the common HQP contract is portable across Edge, mobile, and legacy-hardware contexts.

## Non-claims

HQP-4 repository conformance does not establish:

- physical qualification by itself;
- semantic truth of captured media or syslog content;
- complete observation;
- authenticated UDP source identity;
- legal admissibility;
- regulatory compliance;
- safety certification;
- production readiness;
- qualification of an untested device, firmware, application build, observer build, or environment.
