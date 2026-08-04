# ETS Product Taxonomy

Status: Sprint 0 baseline

## 1. Naming hierarchy

### ETS Protocol

The public, vendor-neutral evidence-transparency specification: schemas, canonicalization profiles, hash and proof profiles, verification outcomes, versioning rules, extension rules, conformance vectors, and security considerations.

The protocol is independently implementable. Conformance does not require an ETS commercial product.

### ETS Community

The free reference implementation and developer adoption path. It includes the local runtime, verifier, CLI, public SDK surfaces, synthetic examples, conformance tooling, and a basic local operator experience.

Community is not represented as a supported production service unless a specific supported offer says otherwise.

### ETS Edge

A supported local evidence-transparency node delivered as software, virtual appliance, or qualified physical appliance. ETS Edge performs near-source ingestion, canonical processing, local append-only logging, proof generation, offline buffering, and optional upstream synchronization.

Profiles may include:

- ETS Edge Virtual;
- ETS Edge Compact;
- ETS Edge Enterprise;
- ETS Edge Air-Gapped;
- ETS Edge Rugged, only after environmental and lifecycle qualification.

### ETS Cloud

A managed service for enrollment, fleet operations, checkpoint synchronization, policy distribution, retained proof material, observability, updates, and customer-controlled export. ETS Cloud is not required for independent proof verification.

### ETS Enterprise

Commercial software and support capabilities for centralized administration, SSO, RBAC, high availability, multi-region deployment, enterprise policy, premium integrations, long-term support, and contractual service levels.

### ETS Assurance

Separately scoped professional services for protocol conformance, deployment review, evidence-process assessment, control-evidence mapping, and verification-readiness reporting. Assurance is not a legal opinion or regulatory certification unless an authorized independent assessor is separately engaged and the contract explicitly says so.

### ETS Support

Commercial technical support covering named products and supported configurations. Support terms define severity, response targets, maintenance windows, lifecycle, exclusions, and customer responsibilities.

## 2. Open and commercial boundary

The following remain openly available:

- protocol specifications and public profiles;
- schemas and algorithm identifiers;
- proof definitions and verifier outcomes;
- golden, negative, malformed, and cross-version vectors;
- local conformance tooling;
- independent offline verification;
- portable proof-bundle formats;
- reference SDK and CLI behavior designated as public.

Commercial offers may charge for:

- production packaging and hardened appliances;
- managed infrastructure and cloud operations;
- enterprise identity, policy, high availability, and fleet management;
- premium connectors and lifecycle support;
- retained proof storage and regional operations;
- warranty, replacement, secure provisioning, and long-term support;
- implementation, integration, training, managed service, and assurance work;
- contractual support, indemnity, service levels, and account management.

Commercial enforcement MUST NOT change canonical protocol semantics, invalidate valid proofs, conceal public verification rules, or prevent customers from exporting their proof material.

## 3. Product maturity states

Every offer is labeled with one of:

- `Research` — exploratory; claims bounded to research artifacts.
- `Development` — active engineering; not supported for production.
- `Preview` — public evaluation; interfaces may change.
- `Controlled Pilot` — approved design-partner scope with explicit limitations.
- `Release Candidate` — feature and protocol candidate awaiting final gates.
- `Generally Available` — approved supported scope with published lifecycle.
- `Deprecated` — supported only under the published deprecation policy.
- `End of Life` — no longer supported after the published date.

Repository visibility or a version tag alone does not imply General Availability.

## 4. Compatibility statements

Approved compatibility language identifies:

- the exact ETS protocol/profile versions tested;
- conformance-suite version and result;
- implementation version;
- optional features tested;
- known deviations and limitations;
- date and environment of the result.

`ETS Compatible` or certification marks require the separate trademark and compatibility-mark policy.

## 5. Claim boundaries

All products preserve the following distinctions:

- node health is not evidence verification;
- evidence verification is not semantic truth;
- captured evidence is not proof of complete observation;
- control mapping is not automatic compliance;
- a proof bundle is not automatic legal admissibility;
- AI analysis is derived evidence and cannot rewrite source evidence or cryptographic state.

## 6. Packaging principles

1. A free user can produce and independently verify meaningful ETS evidence.
2. Paid tiers sell scale, operations, assurance, support, integrations, and managed infrastructure.
3. Entitlements are enforced outside the cryptographic verification path.
4. A subscription ending does not make historical public proofs unverifiable.
5. Customers retain documented export and offboarding paths.
6. Product names never imply certification beyond the actual tested scope.

## 7. Initial customer paths

### Developer adoption

ETS Protocol -> ETS Community -> self-operated implementation or supported ETS offer.

### Small-team deployment

ETS Community evaluation -> ETS Professional or supported ETS Edge Virtual.

### Enterprise deployment

Paid proof of concept -> ETS Edge and ETS Enterprise -> optional ETS Cloud and premium support.

### Government or critical infrastructure

Architecture and security assessment -> controlled pilot -> air-gapped or enterprise appliance profile -> extended lifecycle and specialized support.

### Partner/OEM

Protocol conformance -> partner agreement -> support responsibility matrix -> certified integration, managed service, or embedded implementation.