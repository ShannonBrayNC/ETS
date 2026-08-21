# ETS Vault v1

Status: implementation and appliance qualification contract.

## 1. Purpose

ETS Vault is the durable preservation tier of the ETS product family. Its job is to retain
ETS evidence packages and associated artifacts so that authorized parties can later establish
what was preserved, when it entered the Vault, which retention controls applied, and whether
the preserved bytes still match the recorded cryptographic digest.

Vault is not a generic NAS, backup target, or data lake. It is an evidence-preservation
boundary with explicit write-once semantics, retention, legal hold, cryptographic integrity,
controlled disposition, and independent verification requirements.

The v1 implementation in `ets/vault/` provides the backend-neutral preservation and retention
policy engine. The in-memory backend is a deterministic conformance backend only. A production
ETS Vault appliance MUST bind this engine to a storage implementation that independently
enforces the production capability floor described below.

## 2. Claims and non-claims

Vault v1 is designed to support these claims:

1. preserved bytes are bound to a SHA-256 digest and immutable Vault record;
2. overwrite is prohibited by the storage contract;
3. time-based retention cannot be shortened through the Vault service;
4. compliance-mode retention cannot be downgraded;
5. legal holds prevent disposition;
6. legal-hold release and purge use dual control;
7. administrative state changes are recorded in a hash-chained journal;
8. integrity can be rechecked by reading and hashing the preserved object;
9. production mode fails closed when the configured backend lacks required capabilities.

Vault v1 does **not** claim that a normal local filesystem, file permissions, ZFS snapshot,
or the included in-memory backend constitutes regulatory WORM storage. Production WORM must
be enforced outside the Vault process at the storage boundary.

## 3. Research basis

The appliance requirements were derived from the following standards and current platform
capabilities.

### 3.1 Storage security

- NIST SP 800-209, *Security Guidelines for Storage Infrastructure* (2020), establishes
  storage-specific guidance for data protection, isolation, restoration assurance, encryption,
  access control, configuration management, and recovery.
- NIST published the initial public draft of SP 800-209 Rev. 1 on July 22, 2026. The draft
  reflects current object, virtualized, and software-defined storage security concerns. It is
  informative for Vault design but is not treated as a final normative standard.

References:
- https://csrc.nist.gov/pubs/sp/800/209/final
- https://csrc.nist.gov/pubs/sp/800/209/r1/ipd

### 3.2 Media sanitization

NIST SP 800-88 Rev. 2 (September 2025) shifts sanitization toward an enterprise program and
recognizes cryptographic erase while directing implementers to current media-specific
standards. Vault decommissioning and media replacement procedures MUST follow an approved
sanitization program rather than assuming file deletion is sufficient.

Reference: https://csrc.nist.gov/pubs/sp/800/88/r2/final

### 3.3 Key management and cryptographic modules

- NIST SP 800-57 Part 1 Rev. 5 provides key-management guidance for key protection, inventory,
  backup, compromise, recovery, and trust anchors.
- FIPS 140-3 defines security requirements for cryptographic modules. Federal/high-assurance
  Vault SKUs SHOULD use a validated cryptographic module where required by the deployment.

References:
- https://csrc.nist.gov/pubs/sp/800/57/pt1/r5/final
- https://csrc.nist.gov/pubs/fips/140-3/final

### 3.4 Platform and device trust

- NIST SP 800-193 requires platform firmware resiliency mechanisms that protect, detect, and
  recover from unauthorized firmware changes.
- TCG TPM 2.0 provides the hardware root used for device identity, measured boot, sealed key
  material, and attestation. The current TCG TPM 2.0 Library is Version 185 (March 2026).

References:
- https://csrc.nist.gov/pubs/sp/800/193/final
- https://trustedcomputinggroup.org/resource/tpm-library-specification/

### 3.5 WORM retention patterns

Both Azure Immutable Blob Storage and Amazon S3 Object Lock expose the preservation primitives
Vault needs from a production object boundary:

- versioned/write-once objects;
- time-based retention;
- legal holds;
- a stronger compliance/locked state in which retention cannot be shortened;
- separate authorization for hold and retention administration.

Azure locked time-based policies cannot be deleted or shortened. S3 Object Lock compliance
mode prevents protected object versions from being overwritten or deleted, including by the
account root user, until retention expires.

References:
- https://learn.microsoft.com/en-us/azure/storage/blobs/immutable-storage-overview
- https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html

### 3.6 Time evidence

RFC 3161 defines a Time-Stamp Protocol for establishing evidence that a datum existed before a
particular time. Vault v1 does not require an RFC 3161 TSA, but production deployments MAY
periodically timestamp or externally anchor Vault journal heads to strengthen long-term
independent time evidence.

Reference: https://www.rfc-editor.org/rfc/rfc3161.html

## 4. Threat model

Vault MUST assume that attackers may obtain one or more of the following:

- administrative credentials;
- application-level service credentials;
- access to the host operating system;
- network adjacency;
- access to backup media;
- a retired or replaced storage device;
- the ability to submit malformed or oversized preservation requests;
- the ability to attempt retention shortening, hold removal, rollback, or selective deletion.

Production Vault additionally assumes a storage administrator may be malicious. This is why
WORM enforcement cannot live only in the Vault application process.

Vault v1 does not claim to survive physical destruction of all replicas, destruction of all
cryptographic keys, or compromise of every independent trust/anchor location.

## 5. Logical architecture

```text
ETS Edge / Gateway / AI Witness / Core
                  |
                  v
          Vault ingest boundary
                  |
      +-----------+-----------+
      |                       |
      v                       v
Vault policy engine      Integrity binding
      |                  SHA-256 + ETS refs
      v                       |
Production WORM backend <-----+
      |
      +--> retention / legal hold
      +--> encrypted durable object
      +--> local redundancy / replica
      |
      v
Hash-chained admin journal
      |
      +--> ETS transparency log anchor
      +--> optional RFC 3161/external anchor
```

The evidence bytes and their retention boundary are separate from interpretation and policy
engines elsewhere in ETS. Vault preserves evidence; it does not decide what the evidence means.

## 6. Vault object model

Each Vault object contains a logical `VaultRecord` with:

- unique opaque Vault object ID;
- SHA-256 content hash;
- byte size and media type;
- tenant and workspace scope;
- optional source ETS event ID;
- receive timestamp;
- retention mode and retain-until timestamp;
- zero or more named legal holds;
- monotonically increasing policy generation;
- purge timestamp after authorized disposition.

Object IDs are deliberately opaque and are not raw content hashes. This prevents the Vault ID
itself from becoming a cross-tenant content-deduplication oracle.

## 7. Retention semantics

### Governance

Governance mode provides managed write-once retention. Vault v1 still refuses retention
shortening through its policy engine. A future explicitly privileged governance-bypass workflow
MUST be a separate audited operation if the product ever supports one.

### Compliance

Compliance mode is the default for Vault preservation. It may not be downgraded. Retention may
only remain unchanged or move later.

### Legal hold

A legal hold is independent of time-based retention. Multiple named holds may be active on one
object. Purge is prohibited while any hold is active.

Hold release requires two distinct authorized principals in the v1 service contract. Production
RBAC must also confirm both principals hold the required records-disposition role.

### Purge

Purge is allowed only when all of the following are true:

1. time-based retention has expired;
2. no legal hold is active;
3. dual-control authorization is present;
4. the production backend independently permits deletion;
5. the operation is audit recorded.

The catalog retains a tombstone after payload deletion so the preservation/disposition history
does not disappear with the bytes.

## 8. Production backend capability floor

When `VaultPolicy(require_production_backend=True)` is used, the backend must declare all of
the following capabilities and use an independent `storage` enforcement boundary:

- write-once object creation;
- storage-enforced retention;
- non-bypassable compliance lock for the configured trust model;
- legal hold;
- encryption at rest;
- durable writes;
- administrative audit logging;
- redundant/replicated storage;
- hardware-backed key protection;
- storage-boundary enforcement outside the Vault application process.

The included `InMemoryVaultBackend` intentionally fails this production qualification.

## 9. Hardware appliance requirements

### 9.1 Baseline Vault appliance

Minimum production design target:

- x86-64 platform with UEFI Secure Boot;
- discrete TPM 2.0;
- 8 or more modern CPU cores;
- 32 GB ECC RAM minimum, 64 GB preferred;
- dedicated mirrored OS devices separate from evidence media;
- enterprise evidence SSD/NVMe with power-loss protection;
- redundant evidence layout able to tolerate at least one device failure;
- dual 2.5 GbE or faster network interfaces;
- physically separate or logically isolated management interface where practical;
- chassis intrusion/tamper indication;
- UPS integration and graceful-shutdown support;
- monitored temperature, storage health, and power state.

### 9.2 Vault Enterprise / regulated SKU

Recommended additions:

- 10/25 GbE data interfaces;
- redundant hot-swap power supplies;
- larger ECC memory footprint;
- hot-swap enterprise storage;
- dual-parity or equivalent multi-device failure tolerance;
- dedicated FIPS 140-3 validated HSM where the customer/regulation requires it;
- remote-attestation capable TPM/device identity;
- second Vault or immutable cloud replica in a separate failure domain.

### 9.3 Storage separation

OS/runtime storage and evidence preservation storage MUST be distinct failure and administrative
boundaries. Reimaging the Vault operating system must not require rewriting preserved evidence
media.

## 10. Boot, firmware, and device identity

Production Vault SHALL:

- enable UEFI Secure Boot;
- use TPM 2.0 measured boot and sealed device secrets;
- maintain a unique device identity enrolled in the ETS fleet control plane;
- reject unsigned production firmware/software updates;
- record firmware and software version changes as ETS evidence;
- support a protected recovery image or recovery path;
- alert on boot-measurement or firmware-integrity drift.

These requirements align with the protect/detect/recover model in NIST SP 800-193.

## 11. Cryptographic requirements

- SHA-256 remains the current ETS content digest for Vault v1.
- Data encryption keys MUST not be stored plaintext beside encrypted evidence.
- Device and key-encryption keys SHOULD be non-exportable where the hardware supports it.
- Key rotation MUST NOT make retained evidence unreadable.
- Backup/escrow procedures for required recovery keys MUST be explicit and tested.
- Key destruction is a separate controlled disposition action because loss of a key can make
  otherwise immutable evidence permanently unavailable.
- Federal/regulated deployments MUST select validated modules and algorithms according to their
  governing profile; the reference software does not itself claim FIPS validation.

## 12. Network and identity boundary

Default production posture:

- no direct inbound Internet exposure;
- management and evidence-ingest interfaces separated where possible;
- TLS for remote administrative and ingest traffic;
- mTLS or equivalent device authentication for appliance-to-appliance trust;
- RBAC for custodian, verifier, records administrator, security administrator, and auditor roles;
- MFA enforced by the management identity provider for human administrative actions;
- no retention or hold control accepted solely from untrusted object metadata;
- secrets never passed in command-line arguments or persisted in logs.

## 13. Audit and anchoring

Every state-changing Vault operation produces a hash-chained `VaultJournalEntry` containing:

- contiguous sequence number;
- operation;
- object ID and record generation;
- primary actor;
- second actor when dual control is required;
- reason;
- UTC timestamp;
- previous journal hash;
- current entry hash.

`VaultService.verify_journal()` recomputes the chain and detects changes to any journal entry.
A hash chain alone does not prevent an administrator from rewriting the entire history. A
production Vault MUST periodically export/anchor the journal head into an independent ETS log
and SHOULD support an additional external checkpoint channel for high-assurance deployments.

## 14. Integrity scrubbing

A production appliance SHALL run scheduled integrity scrubs:

1. read preserved object bytes;
2. recompute SHA-256;
3. compare byte size and hash to the Vault record;
4. report storage read errors;
5. emit an ETS evidence event for the scrub result;
6. repair from a verified replica only when the preservation policy permits repair;
7. retain both the original failure evidence and repair evidence.

The implementation exposes `verify_integrity()` as the core primitive for this workflow.

## 15. Backup, replication, and disaster recovery

Vault is not protected merely because the primary copy is immutable. Production deployments
must define:

- replica count and failure domains;
- RPO/RTO;
- encrypted replication transport;
- independent retention on replicas;
- key-recovery procedures;
- periodic restore/read verification;
- rollback detection using trusted Vault/ETS checkpoints.

A replica that can be silently rolled back is not sufficient evidence preservation.

## 16. Sanitization and decommissioning

Device replacement and end-of-life procedures SHALL be documented. Sanitization decisions must
follow NIST SP 800-88 Rev. 2 and the applicable media/vendor standard. The Vault must retain a
sanitization certificate/evidence record outside the destroyed media when policy requires it.

Cryptographic erase may be appropriate for encrypted media only when key scope, key copies,
key backup, and zeroization semantics make the claimed erase valid.

## 17. API/service behavior implemented in v1

The current Python service exposes backend-neutral operations:

- `preserve()`;
- `read()`;
- `get_receipt()`;
- `verify_integrity()`;
- `extend_retention()`;
- `apply_legal_hold()`;
- `release_legal_hold()`;
- `purge()`;
- `verify_journal()`.

The service validates expected content hashes, prohibits retention weakening, keeps legal hold
separate from retention time, and fails production initialization if the backend capability
floor is not met.

## 18. Test matrix

`tests/unit/test_vault_service.py` covers:

- preserve and integrity verification;
- expected-hash mismatch rejection;
- expired retention rejection;
- retention extension;
- retention-shortening rejection;
- compliance-mode downgrade rejection;
- governance-to-compliance upgrade;
- legal hold blocking purge;
- dual-control hold release;
- dual-control purge after retention expiry;
- hash-chain verification and tamper detection;
- production qualification rejection of the test backend.

## 19. Remaining appliance qualification work

Before marketing a physical unit as production ETS Vault, complete these gates:

1. implement and qualify at least one storage-boundary WORM adapter;
2. add durable catalog storage with crash-consistent policy/journal updates;
3. add multipart/streaming ingest so artifact size is not memory bounded;
4. add TPM enrollment, measured-boot evidence, and sealed device keys;
5. add HSM integration profile for regulated/Federal deployments;
6. add authenticated Vault API and fleet registration;
7. add periodic scrub scheduler and ETS event emission;
8. add replica/restore qualification and rollback tests;
9. add power-loss/fault-injection burn-in;
10. add media sanitization/decommission runbook;
11. add independent journal-head anchoring;
12. perform hardware security and recovery qualification on the selected production BOM.

These are explicit qualification gates rather than hidden assumptions. The v1 core is the policy
and integrity foundation on which those appliance adapters are built.
