# ETS Intellectual-Property and Disclosure Boundary

Status: Sprint 0 baseline

## Purpose

This policy prevents accidental publication of confidential filing material or unfiled inventive subject matter while allowing the ETS protocol, verifier behavior, conformance vectors, and reference implementation to remain publicly usable.

This document is operational guidance, not legal advice. Patent, trademark, licensing, and export-control decisions requiring legal judgment remain human gates.

## Public-safe material

The following may be published after normal technical, security, and disclosure review:

- normative interoperability requirements already cleared for publication;
- versioned schemas, algorithm identifiers, proof formats, verifier outcomes, and conformance vectors;
- reference implementation source code approved for Apache-2.0 distribution;
- threat models, security considerations, public roadmaps, and implementation guidance;
- high-level patent-pending notices without confidential filing identifiers;
- factual compatibility and limitation statements supported by retained evidence.

## Restricted material

The public repository MUST NOT contain:

- USPTO receipts, confirmation numbers, application serial numbers unless the owner and counsel explicitly approve publication;
- filing drafts, unpublished claims, claim charts, inventor declarations, assignment strategy, or prosecution correspondence;
- confidential prior-art analysis, attorney work product, legal opinions, or counsel notes;
- customer evidence, credentials, private keys, secrets, production identifiers, or non-public contracts;
- unfiled invention disclosures or diagrams that reveal potentially patentable improvements before review;
- statements representing legal conclusions about freedom to operate, enforceability, validity, infringement, or guaranteed patent coverage.

## Classification

Every protocol-sensitive public artifact is classified as one of:

1. `FILED_OR_PREVIOUSLY_DISCLOSED` — materially covered by an approved filing or prior authorized public disclosure.
2. `INTEROPERABILITY_DETAIL` — necessary public detail that is not believed to add inventive subject matter.
3. `OPEN_SOURCE_IMPLEMENTATION` — implementation detail intentionally released under the repository license.
4. `TRADE_SECRET_OR_CONFIDENTIAL` — operational know-how or information intentionally retained outside the public repository.
5. `POTENTIALLY_PATENTABLE_IMPROVEMENT` — new mechanism, combination, optimization, or application requiring owner/counsel review before disclosure.
6. `UNRESOLVED` — classification is uncertain; publication is blocked.

## Mandatory review triggers

Pre-publication owner and IP review is required when a change introduces or materially changes:

- canonicalization or hash-preimage construction;
- Merkle layout, proof compression, consistency, federation, or anti-equivocation mechanisms;
- evidence completeness, omission detection, trust evaluation, or policy-bound scoring;
- edge/cloud synchronization, offline reconciliation, trusted time, device attestation, or key custody;
- privacy-preserving proof, selective disclosure, redaction, or encrypted evidence binding;
- novel AI provenance, model accountability, autonomous workflow, or cross-domain evidence architecture;
- new protocol claims described as novel, unique, first, patentable, or proprietary.

## Review record

The pull request or linked private record MUST identify:

- artifact paths;
- classification;
- reviewer and date;
- related filing/public disclosure at a non-confidential level;
- publication decision;
- conditions or redactions;
- follow-up filing decision if applicable.

Sensitive detail belongs in an approved private system, not a public issue or pull request.

## Licensing boundary

The repository currently uses Apache License 2.0 for covered source contributions. Apache-2.0 includes a contributor patent grant limited to claims necessarily infringed by the contributor's contribution, subject to its terms. It does not grant trademark rights and does not by itself define a broader standards-essential patent commitment.

Any additional patent pledge, non-assert commitment, defensive termination term, standards-essential patent policy, or certification license requires separate owner and counsel approval.

## Commercial boundary

Open protocol publication does not require publication of:

- hosted-service operations;
- manufacturing and provisioning procedures;
- customer-specific integrations;
- support tooling and internal runbooks;
- commercial pricing, discounts, contracts, or partner terms;
- confidential detection, capacity, reliability, or security operations.

Commercial features MUST NOT alter the meaning of a valid public proof or prevent independent verification after a subscription ends.

## Claim discipline

Public materials MUST distinguish:

- `cryptographically verified` from `factually true`;
- `record included` from `all expected records observed`;
- `tamper evident` from `tamper proof`;
- `control evidence available` from `compliant`;
- `exported evidence package` from `legally admissible evidence`;
- `patent pending` from `patented`, `exclusive`, or `freedom to operate`.

## Publication stop conditions

Publication is blocked when:

- classification is `UNRESOLVED`;
- a potentially patentable improvement lacks required review;
- confidential filing or customer material is present;
- the change would expose a secret, private key, credential, or production identifier;
- public claims exceed retained technical or empirical evidence;
- license ownership or contributor authority is unclear.

## Incident response

If restricted material is published:

1. stop further distribution where practical;
2. notify the project owner and security/IP contacts;
3. preserve a private incident record;
4. remove or rotate exposed secrets immediately;
5. obtain legal guidance before rewriting public history for patent material;
6. document the remediation without repeating sensitive content;
7. update tests and release gates to prevent recurrence.