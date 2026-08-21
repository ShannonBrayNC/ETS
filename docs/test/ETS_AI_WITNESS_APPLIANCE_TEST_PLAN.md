# ETS AI Witness Physical Appliance Test Plan

Status: pilot qualification plan  
Profile: `ets.ai-witness.appliance.pilot.v1`

## 1. Purpose

This plan separates software-contract validation from tests that require the named physical AI Witness appliance. Passing CI is necessary but is not evidence that TPM, Secure Boot, power-loss, storage, thermal, or network behavior has been qualified on hardware.

## 2. Automated software gates

The appliance unit suite validates:

1. Pilot readiness succeeds only when required TPM, boot, clock, adapter, and enrollment evidence is present.
2. Exportable production key declarations and reused signing/sealing key identities fail pilot readiness.
3. Disabled Secure Boot fails pilot readiness.
4. NTS clock evidence cannot declare unauthenticated transport.
5. Runtime adapters cannot be constructed as unauthenticated sources.
6. Fleet enrollment verifies only under the configured Gateway key, valid time window, and verifier-owned expected tenant/workspace/fleet/Gateway/Witness/device-key/nonce/signing-key binding.
7. Fleet enrollment fails under the wrong key, outside its validity window, or when any expected scope/device/nonce field differs.
8. Signed update manifests verify only when signer identity, release sequence, metadata version, expiry, and signature satisfy verifier-owned update policy.
9. Update release rollback/equality is rejected.
10. Update metadata rollback/equality is rejected.
11. Expired update metadata, wrong signer identity, and signed-manifest tampering are rejected.
12. Downloaded update targets must match both declared byte size and SHA-256 digest before activation.
13. Encrypted queue records survive close/reopen before acknowledgement.
14. Complete signed queue records are not stored as plaintext JSON.
15. Duplicate immutable record digests are rejected.
16. Queue opening with the wrong key fails closed.
17. Ciphertext modification is detected before replay.
18. Acknowledged queue entries are removed deterministically.

Run:

```bash
python -m pytest tests/unit/test_ai_witness.py tests/unit/test_ai_witness_appliance.py -q
ruff check ets/ai_witness tests/unit/test_ai_witness.py tests/unit/test_ai_witness_appliance.py
mypy ets/ai_witness
python -m compileall -q ets/ai_witness
```

Repository CI/security/formal checks remain authoritative for merge.

## 3. TPM qualification

On each named reference hardware revision:

- record TPM manufacturer, firmware, profile/capability output, and EK/AK identifiers;
- create evidence signing, attestation, and queue-sealing keys as distinct TPM objects;
- prove production key attributes prohibit private-key export;
- verify signing continues after normal reboot without exporting key bytes;
- rotate to a second signing key while historical records remain verifiable under the first;
- revoke/disable the first key for new signing;
- quote selected SHA-256 PCRs using a verifier-generated random nonce;
- verify the quote under the enrolled attestation public key;
- replay the event log and bind reconstructed PCR state to the quote;
- compare the measured state to approved reference values/RIM policy;
- demonstrate stale quote replay fails because the nonce does not match.

## 4. Secure/Measured Boot qualification

Baseline boot:

- Secure Boot enabled;
- approved firmware/bootloader/kernel/initramfs;
- TPM event log captured;
- reference PCR state recorded under the qualification image.

Negative variants:

- disable Secure Boot;
- modify or replace an unsigned boot component;
- boot an alternate signed but unapproved image;
- modify kernel command line / policy-relevant configuration;
- remove/corrupt the event log where possible.

Expected result: the device must become `unqualified` or `unknown`; it must not silently retain `healthy` qualification.

## 5. Durable queue and power-cut matrix

Execute abrupt power removal at each point:

1. before event validation;
2. after signing but before queue transaction;
3. during queue transaction;
4. immediately after local durable acknowledgement;
5. during upstream transmission;
6. after upstream receipt but before local acknowledgement processing;
7. during local queue acknowledgement/removal;
8. during WAL checkpoint;
9. while queue is near configured capacity.

After each power restoration:

- SQLite integrity check passes or the appliance fails closed;
- no locally acknowledged immutable record is silently missing;
- duplicate replay is idempotent;
- ciphertext/authentication failures are surfaced;
- session chain continuity can still be verified;
- sync resumes from deterministic pending state.

Repeat enough cycles to produce an explicit qualification confidence statement; do not infer endurance from a single power cycle.

## 6. Storage confidentiality/integrity tests

- remove the NVMe and inspect offline;
- confirm complete Witness records are encrypted at the application queue layer;
- confirm full-volume encryption is enabled in the pilot image if adopted;
- modify queue ciphertext and verify authenticated decryption fails;
- modify plaintext record-digest index and verify record/index binding fails;
- substitute a database from another appliance/key ID and verify startup fails;
- simulate storage-full and reserved-space thresholds;
- confirm backpressure occurs before the system reports false successful capture.

## 7. Signed update qualification

Positive path:

- valid newer release sequence and metadata version;
- expected signing-key identity and valid signature;
- target hash and size match the signed manifest;
- update installation;
- reboot into updated image;
- re-attestation under new approved baseline.

Negative paths:

- invalid signature;
- wrong signer/key ID;
- target content changed after signing;
- target size mismatch;
- expired metadata;
- same or lower metadata version;
- same or lower release sequence;
- valid old release that policy marks revoked;
- update interrupted at download, write, bootloader switch, and first boot;
- loss of network between metadata and target retrieval.

Recovery must return either to the previous approved image or an authenticated recovery image and require re-attestation before qualification.

## 8. Clock qualification

Test:

- normal NTS synchronization;
- NTS server certificate/authentication failure;
- fallback to unauthenticated NTP when policy permits;
- no network time source;
- wall-clock rollback;
- wall-clock forward jump;
- excessive offset/uncertainty;
- reboot with RTC drift;
- stale last-sync state.

Verify source time and Witness observation time remain distinct and that monotonic retry/duration behavior is not corrupted by wall-clock changes.

## 9. Runtime adapter qualification

For each supported provider/runtime adapter:

- authenticate the peer using the documented method;
- verify tenant/workspace derives from server-owned enrollment/source mapping;
- attempt payload tenant/workspace spoofing;
- attempt replay of adapter messages;
- send oversized event material;
- send unknown/raw prompt/output fields;
- verify digest-only capture;
- verify adapter version/source identity is retained;
- verify provider outage and reconnect behavior;
- verify adapter gap/liveness state can be distinguished from healthy observation.

## 10. Gateway/fleet enrollment qualification

- enroll a new Witness under a fresh verifier nonce;
- verify device-key fingerprint binding;
- verify tenant/workspace/fleet/Gateway/Witness/signing-key scope;
- reject any expected-scope mismatch even when the enrollment signature is otherwise valid;
- reject an enrollment carrying the wrong freshness nonce;
- reject expired/future enrollment;
- reject replay to another Witness identity/device key;
- rotate enrollment signer;
- revoke device and verify new upstream authorization fails;
- test bounded offline operation after revocation issuance and document the standing policy;
- re-enroll after approved recovery/reprovisioning.

## 11. Seven-day appliance soak

The physical pilot must complete a named seven-day soak with:

- sustained representative AI event workload;
- periodic burst workload;
- scheduled upstream disconnect/reconnect;
- clock-source disruption;
- controlled service restart;
- queue growth and replay;
- periodic TPM attestation;
- update check without update activation;
- thermal, CPU, memory, NVMe wear/health, queue depth, and sync metrics captured.

No silent evidence loss, unexplained duplicate immutable content, unrecoverable queue failure, or signing-key exposure is permitted.

## 12. Exit evidence pack

The qualification pack should contain:

- exact hardware BOM/revisions/firmware;
- OS/image digest and release sequence;
- TPM capability and attestation evidence;
- Secure Boot state and measured-boot baseline;
- test logs/results for all negative/positive cases;
- power-cut matrix results;
- seven-day soak metrics;
- update/recovery evidence;
- clock qualification evidence;
- adapter/enrollment evidence;
- known limitations and waived findings;
- independent reviewer approval tied to exact artifact hashes.
