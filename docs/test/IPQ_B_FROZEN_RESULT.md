# IPQ-B Frozen Edge Virtual Result

Parent: #319  
Execution sprint: #351  
Qualification run: `31866484647`  
Frozen SUT: `75927c5a6c3f35e56c4f6e2cd88947e18a2ff333`

## Overall disposition

**QUALIFICATION COMPLETE — FUNCTIONAL LIFECYCLE PASS WITH FROZEN CREDENTIAL-AT-REST FAILURE.**

The immutable frozen Edge baseline reproduces the controlled capture/proof/synchronization lifecycle, restart recovery, duplicate-safe replay and raw synchronization-payload exclusion. It does **not** satisfy the parent requirement that a reusable local API credential be persisted without exposing the reusable secret itself.

PR #334 is later repair evidence only. It does not change the frozen disposition.

## Retained evidence

| Evidence family | Result | Artifact ID | Artifact ZIP SHA-256 |
| --- | --- | ---: | --- |
| Frozen Edge-native tests | PASS — 41 tests | `9242163652` | `0c3062aa16c9d006cb24bfece4cc440f2438ce67488ca94832aac8c47b09701d` |
| Detached lifecycle / secret-boundary probe | PASS harness; mixed product disposition | `9242163833` | `a9a7582fe41293d4bbd9b635f71c50c9c32ee616168cd4cad7dc8007df63ac0c` |

Both jobs asserted the exact frozen SUT SHA before execution and retained the qualification harness SHA.

## Mandatory scenario disposition

| Parent scenario | Disposition | Evidence boundary |
| --- | --- | --- |
| First boot creates stable local credential and software-held identity | **PARTIAL / FAIL security clause** | Credential is strong and mode `0600`, but the reusable API key itself is persisted in plaintext. Software identity remains `software_volume`; `hardware_attested=false`. |
| Restart preserves identity/API-key behavior | **PASS** | Frozen device-identity tests plus detached first-boot/reload probe. No hardware-attestation claim. |
| JSON webhook exact-byte capture and modified-byte digest behavior | **PASS** | Frozen webhook/protected-ingress suite within controlled test inputs. |
| RFC 5424 syslog exact-datagram capture and malformed diagnostics | **PASS** | Frozen syslog adapter suite within UDP lab boundary. No production transport-security claim. |
| Inclusion proof / portable verification behavior | **PASS** | Frozen Edge runtime proof-facade suite. |
| Upstream outage -> local durable capture -> restart -> reconnect -> synchronize | **PASS** | Detached probe queues while upstream is absent, reconstructs the SQLite queue after restart, reconnects to frozen upstream acceptance, drains and marks synchronized. |
| Repeated synchronization is duplicate-safe | **PASS** | Detached replay receives the same acknowledgement and upstream accepted-record count remains one; native upstream suite independently covers idempotency/conflict behavior. |
| Queue capacity / pre-capture backpressure | **PASS** | Frozen sync-queue suite exercises capacity failure/backpressure. |
| Raw webhook/syslog marker content absent from synchronization/upstream payload | **PASS within selected frozen profile** | Native upstream suite refuses `raw_payload_included=true`; detached sync payload has `raw_payload_included=false` and no `raw_payload` field. This is not a universal source-content non-retention claim outside the exercised paths. |
| Reusable secret protected at rest | **FAIL** | Frozen `load_or_create_local_api_key()` persists the API key itself; the frozen unit test explicitly asserts file contents equal the key. Mode `0600` restricts filesystem permissions but does not encrypt or one-way protect the credential. |

## Post-baseline repair boundary

PR #334 introduced later secret-file / encrypted-verifier hardening. It may be cited as repaired-candidate evidence only. The frozen baseline remains failed for the credential-at-rest requirement and must never be described as having #334 behavior.

## Claim boundary

This qualification establishes only the controlled software Edge behaviors reproduced against the frozen SHA. It does not establish:

- TPM/HSM custody or hardware attestation;
- physical device provenance;
- source truth or source completeness;
- production-grade UDP transport security;
- high availability or production GA;
- legal admissibility or compliance certification;
- a claim that raw source content can never appear in any untested metadata path.

## Finalization rule

This retained result may be merged after the qualification branch is synchronized to then-current `main`, all exact-head repository gates are green, and a fresh independent LanternProtocol review approves that synchronized head. Closing #319 after merge means the frozen qualification has a recorded disposition; it does **not** mean the frozen security failure became a PASS.
