# ETS Edge MVP Contract

Status: Sprint E0 baseline candidate
Date: 2026-08-01
Parent: #140
Related: #141, #157

## Product objective

ETS Edge MVP is a deployable evidence-transparency node that captures approved source events or evidence references near their origin, preserves canonical digests and provenance, appends records to a durable local transparency log, generates independently verifiable proof material, survives bounded disconnection, and synchronizes signed checkpoints and records to an upstream ETS service.

ETS Edge MVP is not a SIEM, EDR, forensic acquisition suite, autonomous remediation system, legal-admissibility engine, or regulatory certification product.

## Authoritative baseline

The authoritative implementation baseline is the protected `main` branch after the v0.1.0-alpha freeze is completed through issue #157. Feature branches are not product baselines. Edge implementation work must branch from the exact merged-main commit recorded by the alpha validation record.

## Initial deployment targets

### Primary

- x86-64 Ubuntu LTS appliance or virtual machine.
- Minimum pilot target: 4 CPU cores, 16 GiB RAM, and 512 GB high-endurance SSD/NVMe.
- TPM 2.0 is preferred but is not required for the first software-key pilot profile.

### Secondary

- OCI container for development, CI, integration testing, and controlled laboratory use.
- The container profile is not the initial physical-appliance security boundary.

### Deferred

- ARM64 and Raspberry Pi qualification.
- Ruggedized or industrial hardware.
- Kubernetes as an appliance runtime.
- Multi-node high availability on the edge device.

## MVP use cases

1. Receive authenticated HTTPS/webhook evidence submissions.
2. Receive syslog records through a qualified adapter.
3. Hash files by stream through a drop-folder or file adapter without retaining raw bytes by default.
4. Receive Windows-originated records through Windows Event Forwarding or an equivalent forwarding boundary.
5. Validate and append versioned capture envelopes to durable local storage.
6. Produce signed tree heads, inclusion proofs, consistency proofs, proof bundles, and verification certificates.
7. Operate during a bounded network outage and synchronize later without unexplained loss or unintended duplication.
8. Allow a local operator to inspect device health, source health, queue state, evidence metadata, proof status, synchronization, and administration.
9. Allow an authenticated customer to view fleet usage, synchronized evidence metadata, proof status, storage/retention usage, and administrative audit history.
10. Allow an unauthenticated third party to verify a supplied portable proof bundle without browsing tenant data.

## Initial supported envelope

The MVP sizing target is a qualification objective, not a guaranteed production SLA.

- Sustained ingest target: 50 evidence records per second per node.
- Burst target: 200 records per second for 10 minutes with bounded backpressure.
- Offline operating target: seven days at the sustained target within the supported storage profile.
- Local metadata/proof allocation target: 300 GB usable capacity on the 512 GB reference device after operating-system, update, recovery, and safety reserves.
- Maximum single streamed object for hashing: 10 GB, subject to adapter policy.
- Default maximum webhook payload: 1 MiB, configurable downward by policy.
- Minimum free-space warning: 20 percent.
- Critical ingest backpressure threshold: 10 percent free space.
- Fail-closed threshold: insufficient capacity to commit the complete transaction and required proof metadata.

All limits must be verified in Sprint E6 capacity and resilience testing before customer-facing support claims are approved.

## Portal responsibilities

### Local Edge Operator Portal

Responsible for one node: enrollment status, local health, evidence integrity, storage, queue, sources, synchronization, signer status, backup/restore, updates, diagnostics, and local proof export. It must remain usable during cloud outage.

### Central Customer Portal

Responsible for tenant-scoped fleet inventory, usage, synchronized evidence search, proof and checkpoint status, retention consumption, users, roles, policies, entitlement display, and administrative audit. It must not rewrite local node history or become required for offline verification.

### Public Verification Portal

Responsible only for verifying user-supplied public-safe proof material or identifiers. It must not expose tenant browsing, private evidence, unrestricted identifier enumeration, or unsupported semantic-truth claims.

## Raw-evidence boundary

ETS records canonical metadata, content digests, provenance, evidence-location references, verification material, and lifecycle records. Raw evidence bytes remain in the source system or a separately governed content store by default.

Hashing a file or payload does not authorize ETS to retain, replicate, disclose, or transform its raw content. Any future managed content-store profile requires separate encryption, retention, privacy, deletion, access-control, breach-response, and jurisdiction decisions.

## MVP release claims

The MVP may claim that, for supported versioned inputs, it can verify declared cryptographic properties including canonical digest reproduction, append-log inclusion, proof consistency, signed checkpoint identity, and portable bundle verification.

The MVP must not claim that it independently proves:

- real-world truth or observation completeness;
- legal admissibility or official chain of custody;
- actor intent or attribution not supplied by the source;
- regulatory compliance or certification;
- absence of omitted events;
- correctness of an AI conclusion;
- security of the originating system.

## MVP non-goals

- AI correlation or automated remediation.
- Universal trust scoring.
- Compliance-percentage dashboards.
- Connector marketplace.
- Full Microsoft 365 connector suite.
- Evidence Graph persistence or causal reasoning.
- Multi-region cloud or edge high availability.
- General availability, warranty, or regulated-industry certification.

## Release gates

- Alpha freeze completed on one exact merged-main commit.
- Protocol vectors and API contracts recorded and reproducible.
- Edge protocol profile and capture-envelope schema approved.
- Required ADRs approved through independent review.
- No critical runtime change remains only on an unresolved branch.
- Full CI, security, recovery, migration, portal, and appliance qualification gates pass for the MVP candidate.
- Controlled design-partner pilot completes before any general-availability claim.
