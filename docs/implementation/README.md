# ETS Implementation Guides

This directory contains public-safe implementation guidance for ETS vertical integrations, developer onboarding, security hardening, certificate generation, and public verification experiences.

## Current guides

- [ETS Developer Quickstart: 15-Minute Proof Pipeline](ETS_DEVELOPER_QUICKSTART.md) - hands-on developer guide for installing ETS, creating a fictional EvidenceEvent, appending it, generating and verifying a Merkle proof, rendering a certificate, policy-routing the result, and running the local API and lab UI.
- [ETS Security Hardening Guide](ETS_SECURITY_HARDENING_GUIDE.md) - deployment and repository hardening guide covering auth modes, tenant/workspace scoping, redaction, signing, secret scanning, certificate boundaries, backup/restore, and release gates.
- [ETS Certificate and Public Verifier Guide](ETS_CERTIFICATE_PUBLIC_VERIFIER_GUIDE.md) - implementation guide for claim-safe JSON, Markdown, and HTML certificates, public verifier APIs, offline verification, manifest publication, and certificate tests.
- [ETS Vertical Implementation Guide](ETS_VERTICAL_IMPLEMENTATION_GUIDE.md) - detailed implementation guide across AI governance, DevSecOps, enterprise compliance, healthcare, insurance, finance, civic/public-sector, emergency/sensor, legal/HR, and Lantern ecosystem integrations.
- [Building Transparency in Election Systems with ETS](ELECTION_TRANSPARENCY_IMPLEMENTATION_GUIDE.md) - public-safe implementation guide for election-adjacent transparency layers, expected-event policies, evidence manifests, proof bundles, certificates, and Python examples.

## Boundary

These guides use fictional, local-only, non-PII examples. Do not add production customer evidence, official election data, medical records, financial records, legal records, secrets, credentials, USPTO receipts, application numbers, claim charts, prior-art matrices, attorney-review notes, or assignment strategy to this directory.

ETS verifies submitted-event metadata, hashes, inclusion proofs, tree-head material, verification certificates, and policy-routing records. ETS does not prove real-world truth, legal sufficiency, election correctness, raw evidence authenticity, official chain of custody, vote totals, ballot validity, or completeness without an external expected-event policy and observation process.
