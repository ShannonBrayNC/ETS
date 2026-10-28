# ETS Go-to-Market Plan

Decision date: 2026-10-28  
Status: Agreed product and deployment direction; implementation and release qualification remain separate.

## Strategy

Launch ETS (Evidence Transparency System) through a freely accessible Windows
verifier, then grow adoption into paid hosted services and enterprise Edge/fleet
deployments. The Microsoft Store distributes the user-facing client. Continuous
collection and shared trust services have separate deployment and update paths.

ETS provides portable, independently verifiable evidence. Verification must
distinguish cryptographic integrity, signer/source trust, and claims about the
underlying event. A valid proof does not establish real-world truth or completeness.
ETS complements existing operational, security, and audit systems.

This plan records the agreed commercial direction. It does not assert that a
Store-qualified package exists, that Microsoft has certified ETS, or that hosted services
are production-qualified. Existing protocol, security, release, and IP gates remain
in effect.

## Product and distribution model

| Product | Distribution | Customer value | Commercial role |
| --- | --- | --- | --- |
| ETS Verifier / Desktop | Microsoft Store MSIX | Open evidence bundles, verify locally, inspect receipts and signatures, export reports, optionally connect to an ETS endpoint | Free adoption and independent verification |
| ETS Edge for Windows | Publisher-signed MSI, direct or enterprise-managed deployment | Unattended collection, durable offline queues, machine identity, and synchronization | Enterprise deployment and support |
| ETS Core / Gateway / Fleet | Versioned containers in Azure or customer-controlled infrastructure | Shared ingestion, signed checkpoints, tenant services, and fleet operations | Paid hosted subscriptions or enterprise arrangements |
| ETS Edge appliance | Managed Linux appliance/container deployment | Site-local acquisition and offline operation; hardware-backed identity where qualified | Enterprise appliance and support offering |
| ETS developer interfaces | Existing CLI and SDK distribution channels | Integrate evidence generation and verification into applications | Developer adoption and integration pathway |

The initial Store product is **ETS Verifier**. Administration and Edge status can
be added later to the same desktop client. Installing a verifier must not require
installing an unattended collector.

## Audience and route to adoption

The initial users are evidence recipients, auditors, developers, and technical
evaluators who need to inspect an exported bundle without operating ETS
infrastructure. The enterprise buyers are teams that need repeatable collection,
retention, fleet management, and operational support.

The intended adoption sequence is:

1. Discover ETS through the Store, repository, product documentation, or an
   evidence bundle shared by another organization.
2. Install the free verifier and verify a supplied sample or customer-controlled
   bundle locally, without an account.
3. Integrate through the CLI/SDK or optionally connect the desktop client to a
   hosted or customer-controlled endpoint.
4. Evaluate a bounded organizational pilot with explicit data sources,
   acceptance criteria, operational ownership, and evidence export.
5. Adopt paid hosted services or a supported customer-managed/hybrid deployment.
6. Expand Edge coverage and fleet operations after the pilot is qualified.

Store downloads are an adoption signal, not proof of enterprise demand. Pilot
success depends on usable evidence and repeatable operations.

## First release: ETS Verifier

The first Store release should:

- Open supported exported evidence bundles and verify supported hashes, proofs,
  signatures, and receipts locally.
- Work without cloud connectivity, account creation, subscription, or an Edge
  installation for supported self-contained verification workflows.
- Present verified, failed, unsupported, and indeterminate outcomes distinctly;
  missing trust material must not become a successful trust claim.
- Explain the trust material used and the limits of offline verification,
  including freshness or revocation information that cannot be established offline.
- Export readable and machine-readable verification results.
- Optionally connect to hosted ETS or an explicitly configured customer endpoint.
- Keep local verification available when hosted service access is unavailable.

Reuse the existing verifier/core libraries and report contracts. Keep core
protocol code independent of UI, API, and persistence runtime dependencies.
Bundle the required runtime so end users do not need Python, Git, pip, or a
development checkout.

The implemented engineering candidate uses a pywebview/WebView2 Windows host,
a local desktop UI, a separately bundled PyInstaller verifier, and development MSIX
packaging. Native verification/export and program-scoped firewall tests pass in
Windows Server CI. This resolves the initial host experiment; it does not establish
Windows 11 support, signed installation or Store readiness. See the
[readiness evidence and release gates](WINDOWS_VERIFIER_READINESS.md). This plan
does not authorize a protocol rewrite.

## Deployment and update boundaries

### Store desktop client

Use MSIX for the Store client to obtain Store-managed installation and updates.
The client should run as a standard user and store mutable state outside its
installed package. Store package signing establishes distribution trust; it does
not confer trust on evidence signers or their claims.

A portal-only PWA remains a fallback for a narrower web experience, but it is
not the primary plan for dependable local evidence handling and offline
verification.

### Windows Edge agent

Use a signed MSI for the unattended Windows agent, deployable directly or
through enterprise management such as Intune. Qualify installation privileges,
least-privilege service identity, source access, restart recovery, durable queues,
and data-preserving upgrades.

Keep the service release cadence separate from the desktop UI. Updating the
verifier must not restart or disrupt collection. Define authenticated local
communication and supported client/agent versions before adding administration.

MSIX supports some machine services with restrictions; the MSI choice is an
operational boundary, not a claim that MSIX cannot contain services.

### Hosted and customer-managed services

Use immutable, versioned container releases for Core, Gateway, and Fleet in Azure
or customer infrastructure. Qualify production identity, key operations,
tenant isolation, persistence, backup/restore, monitoring, and upgrade recovery.
Do not represent unsigned local development profiles as production trust services.

Preserve offline-first Edge operation and durable synchronization. Preserve the
existing evidence storage boundary: raw evidence bytes are not implicitly
uploaded or retained merely because proof metadata is synchronized.

### Appliances

Offer managed Linux appliance deployments where local acquisition and offline
operation justify them. Claims of hardware-rooted trust require qualified
hardware and key provisioning. Containers or virtual machines alone do not
establish a hardware trust root.

## Commercial model

- **Free verifier:** independent local verification remains freely accessible,
  without a hosted subscription.
- **Paid hosted services:** charge for operating managed services, capacity,
  retention, organizational features, and support.
- **Enterprise:** offer customer-managed or hybrid deployment, Edge/fleet
  operations, integration, and support under an agreed commercial arrangement.
- **Appliances:** offer hardware and operational support where justified by the
  customer's deployment and trust requirements.

Prices, quotas, billing intervals, support commitments, and launch dates are
not set by this decision. The existing pricing/metering document lists candidate
meters; those must not be interpreted as charging for local offline verification.
No billing implementation is implied by this plan.

## Rollout and acceptance gates

| Phase | Deliverable | Exit evidence |
| --- | --- | --- |
| 1. Packaging assessment | Dependency inventory, Windows host choice, package identity, proof-of-concept MSIX | Supported offline verification runs as a standard user on a clean Windows machine without developer tools |
| 2. Verifier beta | Installable desktop candidate and sample bundles | Known-good, tampered, unsupported, and missing-trust cases produce correct outcomes; exports, accessibility, installation, upgrades, and uninstall behavior verified |
| 3. Store launch | Certified ETS Verifier and accurate listing | Publisher identity, privacy/support information, dependency licensing, Windows certification checks, and Store review complete; existing release/IP gates satisfied |
| 4. Organizational pilots | Optional hosted/customer endpoint connection and separately installed Edge | Tenant isolation, authenticated access, offline recovery, queue durability, service continuity, and evidence export demonstrated for the declared pilot scope |
| 5. Commercial expansion | Hosted subscriptions and enterprise fleet/appliance offerings | Production readiness, billing terms, support ownership, recovery procedures, and deployment-specific trust claims qualified |

These phases define an adoption sequence, not a claim that backend engineering
must wait for the Store launch. Engineering work may proceed concurrently while
each product retains its own release gates.

Phase 1 engineering artifacts now exist, but its clean standard-user client exit
criterion is still open. Do not advance to installable beta or Store launch solely
because CI passes. Complete the [release qualification record](WINDOWS_RELEASE_QUALIFICATION_RECORD.md)
for the exact candidate before making a release-readiness claim.

## Success measures and outstanding decisions

Track install-to-first-successful-verification conversion, time to first verified
bundle, verification failure/support patterns, qualified pilot conversion,
pilot-to-paid conversion, and retained organizational usage. Measure offline
activity only through an explicitly chosen privacy-respecting mechanism; offline
verification must not require telemetry or connectivity.

Before commercial launch, decide:

- Supported Windows versions and processor architectures.
- Production qualification of the implemented desktop host/runtime bundle, WebView2
  provisioning, Partner Center identity, and file associations.
- Supported evidence profiles and trust material/freshness behavior.
- Enterprise installer signing, update rings, compatibility policy, and data retention.
- Pricing, quotas, service commitments, and named operational owners.
- Initial pilot scope and numerical success targets.

## Related repository contracts

- [Windows verifier phase 1 readiness and packaging experiment](WINDOWS_VERIFIER_READINESS.md)
- [Deployment model](../architecture/DEPLOYMENT_MODEL.md)
- [Hosted platform requirements](HOSTED_PLATFORM_REQUIREMENTS.md)
- [Pricing and metering model](PRICING_METERING_MODEL.md)
- [Complete solution requirements](../requirements/ETS_COMPLETE_SOLUTION_REQUIREMENTS.md)
- [Service readiness requirements](../requirements/service-readiness/README.md)
- [Core offline verifier contract](../core/ETS_CORE_C3_OFFLINE_VERIFIER_CONTRACT.md)
- [SDK release process](../sdk/RELEASE.md)

## Microsoft distribution references

Reviewed for the 2026-10-28 decision; recheck requirements at submission time.

- [Choose a Windows app distribution path](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/choose-distribution-path)
- [MSIX app package requirements](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/app-package-requirements?pivots=store-installer-msix)
- [Converting an installer with services](https://learn.microsoft.com/en-us/windows/msix/packaging-tool/convert-an-installer-with-services)
- [Publish a PWA to the Microsoft Store](https://learn.microsoft.com/en-us/microsoft-edge/progressive-web-apps/how-to/microsoft-store)
