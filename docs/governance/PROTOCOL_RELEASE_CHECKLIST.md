# ETS Protocol Release Checklist

Use this checklist for every public protocol or profile release candidate. Evidence must identify the exact commit and workflow run. A checked box without retained evidence is not a passing gate.

## Scope and identity

- [ ] Release identifier, protocol version, profile identifiers, and implementation version are explicit.
- [ ] Normative and non-normative content are clearly separated.
- [ ] Changed canonical inputs, schemas, algorithms, signatures, proofs, APIs, and error outcomes are listed.
- [ ] Non-goals and claim boundaries are current.

## Architecture and decisions

- [ ] Every normative change has an approved ADR.
- [ ] Trust boundaries and affected components are documented.
- [ ] Backward, forward, and legacy-verification behavior are specified.
- [ ] Migration, rollback, deprecation, and archival requirements are documented.
- [ ] Unknown critical profiles and downgrade attempts fail closed.

## Specification and interoperability

- [ ] A third party can implement the profile from public material.
- [ ] Protocol, schemas, vectors, and verifier behavior use consistent identifiers.
- [ ] Golden, negative, malformed, replay, downgrade, and cross-version vectors are present.
- [ ] The public conformance runner works locally and in CI without Lantern credentials.
- [ ] The ETS reference implementation passes the same public suite.
- [ ] Independent offline verification succeeds.

## Security and privacy

- [ ] Threat model and security considerations are current.
- [ ] Canonicalization ambiguity, parser differentials, collision assumptions, second-preimage resistance, signature binding, replay, equivocation, and key lifecycle are addressed as applicable.
- [ ] Privacy, metadata leakage, data minimization, raw-content boundaries, and retention are addressed.
- [ ] Security review is submitted by an eligible reviewer.
- [ ] Open vulnerabilities have an explicit release disposition.

## IP, licensing, and disclosure

- [ ] Every public artifact has a disclosure classification.
- [ ] Potentially patentable improvements received required owner/IP review.
- [ ] Restricted filing, attorney, customer, credential, key, and production material is absent.
- [ ] Code, documentation, specification, contribution, trademark, and compatibility-mark terms are identified.
- [ ] No public statement overstates patent status, exclusivity, freedom to operate, or legal conclusions.

## Quality gates

- [ ] Ruff passes at the exact candidate commit.
- [ ] mypy passes at the exact candidate commit.
- [ ] Full pytest passes at the exact candidate commit.
- [ ] Release-readiness checks pass.
- [ ] Dependency and secret scans pass or have approved, time-bounded dispositions.
- [ ] Frontend/build checks pass when affected.
- [ ] Formal, symbolic, mechanized-proof, and benchmark workflows pass when affected.
- [ ] Generated schemas, OpenAPI, vectors, and documentation show no unreviewed drift.

## Claims and documentation

- [ ] Documentation was technically edited for consistency and implementability.
- [ ] Examples use synthetic, non-sensitive data.
- [ ] `verified` is not presented as `true`, `complete`, `compliant`, or `legally admissible`.
- [ ] Performance and scale claims link to retained benchmark or pilot evidence.
- [ ] Compatibility statements identify exact tested scope and known deviations.

## Review, merge, and synchronization

- [ ] Pull-request branch is current with the target branch.
- [ ] Required status checks pass on the final head commit.
- [ ] Independent submitted approval is present.
- [ ] Branch protection and repository rules are satisfied.
- [ ] Merge commit or squash commit is recorded.
- [ ] Post-merge `main` workflows pass.
- [ ] Release tag, if any, points to the approved commit on the default branch.
- [ ] Long-lived development branches are rebased or merged from the updated default branch before new protocol work.
- [ ] Sprint issue contains final evidence and next-sprint readiness notes.

## Human gates

The following cannot be completed by automation alone:

- final IP/legal approval where required;
- independent protocol/security approval;
- public release authorization;
- trademark or certification authorization;
- General Availability approval.