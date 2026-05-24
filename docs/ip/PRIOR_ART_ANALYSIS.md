# ETS Prior Art Analysis

This document organizes technical comparison areas for patent counsel and
research review. It is not legal advice and does not assert patentability.

## Traditional Logging and SIEM

Traditional logging and SIEM systems collect operational records for search,
alerting, and investigation. ETS differs by requiring deterministic evidence
canonicalization, independent proof verification, and hash-only proof bundles.
ETS does not replace SIEM; it can provide verifiable evidence artifacts to
systems that already aggregate logs.

## Audit Systems

Audit systems often rely on database permissions, retention controls, and
operator-managed trails. ETS focuses on independently reproducible evidence
hashes, append-only transparency behavior, and verifier-side proof checks.

## Certificate Transparency

Certificate Transparency is a major prior-art family for Merkle transparency
logs. ETS should not claim generic transparency logs, Merkle inclusion proofs,
or public monitor concepts. Differentiation, if any, must focus on generalized
operational evidence semantics, tenant-scoped verification, proof bundles,
omission-suspicion workflows, and AI accountability evidence chains.

## Blockchain Architectures

Blockchains provide replicated consensus and public ledgers. ETS does not
require a token, consensus chain, or smart-contract execution. ETS uses
transparency and verifier federation as a lighter evidence-verification model.

## OpenTelemetry and Distributed Tracing

OpenTelemetry captures traces, metrics, and logs for observability. ETS focuses
on verifiability: canonical event hashing, proof generation, signature status,
and independent verifier checks. ETS can consume observability metadata but
should not claim tracing itself.

## AI Explainability Systems

Explainability systems attempt to explain model behavior. ETS records evidence
about AI workflow events and supports audit-chain reconstruction. It does not
claim that an explanation is faithful or that a model decision is fair.

## Candidate Differentiators for Review

- protocol-level evidence object lifecycle across heterogeneous systems;
- public proof material separated from private source evidence;
- verifier federation and quorum semantics for evidence proof acceptance;
- omission suspicion based on expected event policies;
- AI operational verifiability through recorded evidence chains.

## Non-Claim Areas

ETS should not claim generic hashing, generic Merkle trees, generic digital
signatures, generic blockchains, generic audit logs, or generic distributed
tracing.
