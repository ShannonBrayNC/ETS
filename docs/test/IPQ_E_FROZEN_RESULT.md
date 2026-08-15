# IPQ-E Frozen Enterprise Result

Frozen SUT: `75927c5a6c3f35e56c4f6e2cd88947e18a2ff333`  
Qualification sprint: #345  
Harness PR: #346  
Initial evidence run: `31858741473`

## Result summary

The detached IPQ-E harness executed the selected frozen enterprise-adapter and Generic REST tests from the immutable SUT repository root. No frozen product file was patched or rewritten.

| Area | Result | Reproduced evidence |
|---|---|---|
| GitHub Audit adapter / controlled source behavior | **PASS** | 11/11 selected tests passed: connector conformance, cursor/time replay, throttling without checkpoint advance, revoked-credential fail-before-source, retention-gap classification, metadata minimization, fixed qualified GitHub origin, server-authoritative scope, local append + durable enqueue before checkpoint release, backpressure withholding, and partial-commit retry recovery. |
| AWS CloudTrail adapter / controlled source behavior | **PASS** | 11/11 selected tests passed: connector conformance, NextToken/time replay, throttling without checkpoint advance, revoked-credential fail-before-source, Event History retention-gap classification, metadata minimization, endpoint/account-scope restriction, server-authoritative scope, commitment ordering, backpressure, and partial-commit retry recovery. |
| Okta System Log adapter / controlled source behavior | **PASS** | 12/12 selected tests passed: connector conformance, server-generated next-link/time replay, throttling without checkpoint advance, revoked-credential fail-before-source, retention-gap classification, minimized network/email/debug fields, qualified Okta origin and next-link validation, server-authoritative scope, commitment ordering, backpressure, and partial-commit retry recovery. |
| Generic REST transport and extraction | **PASS** | 29/29 selected tests passed: HTTPS trusted-host policy, redirect/auth/authorization/throttle/retry classification, credential-destination and static sensitive-value restrictions, timeout/response/header bounds, declarative allow-listed extraction, source-cursor replay, overlapping time-window replay without completeness claim, bounded checkpoint/extraction policy, server-authoritative scope, commitment ordering, backpressure, conflicting retry, and partial-commit retry recovery. |
| Server-authoritative tenant/workspace scope | **PASS** | Each Gateway integration group proves instance/source-provided tenant/workspace values do not override the server-authoritative scope committed by the Gateway path. |
| Checkpoint release after local append + durable enqueue | **PASS** | All four integration groups exercise checkpoint release only after local append and successful durable synchronization enqueue. |
| Pre-commit backpressure behavior | **PASS** | All four integration groups show backpressure withholding append/checkpoint progress before commit. |
| Append-before-enqueue partial-commit recovery | **PASS** | All four integration groups preserve the local append while withholding checkpoint progress, then recover idempotently on retry. |
| Source-side retry / throttle / credential-state handling | **PASS** | Baseline-native unit tests reproduce bounded source-side handling with synthetic clients/credential providers. |
| Retention-gap / replay semantics | **PASS (bounded)** | Frozen unit tests reproduce stale-checkpoint gap classification and checkpoint/time-window replay. This is state/replay semantics, not a container/process restart or proof of source completeness. |
| Live external-service collection with production credentials | **EXCLUDED** | The frozen qualification uses deterministic synthetic clients and credential providers. No claim is made that GitHub, AWS, Okta, or an arbitrary production REST endpoint was live/reachable or correctly permissioned during this run. |
| Source truth or completeness | **EXCLUDED** | The adapters demonstrate bounded observation, minimization and continuity behavior; they do not prove that the upstream source is truthful or complete. |

## Retained evidence

### GitHub Audit

- job: `94948125576`
- tests: `11 passed in 1.40s`
- artifact: `ipq-e-github-audit-frozen`
- artifact ID: `9239846763`
- artifact ZIP SHA-256: `099fa172a17e25ba6770eb255d65fc059ffe83d428fccd1c472207b9393d25ea`

### AWS CloudTrail

- job: `94948125567`
- tests: `11 passed in 0.39s`
- artifact: `ipq-e-aws-cloudtrail-frozen`
- artifact ID: `9239847187`
- artifact ZIP SHA-256: `203a933987b63797fabd9a5eb46c0f39942c10da055459dda818a4f6ead4dfb7`

### Okta System Log

- job: `94948125492`
- tests: `12 passed in 0.42s`
- artifact: `ipq-e-okta-system-log-frozen`
- artifact ID: `9239844981`
- artifact ZIP SHA-256: `da00e59526310f6e70487d1d26c31c083e670cb3c5f39bffaf24d90854445dbc`

### Generic REST

- job: `94948125519`
- tests: `29 passed in 1.64s`
- artifact: `ipq-e-generic-rest-frozen`
- artifact ID: `9239846106`
- artifact ZIP SHA-256: `34fbe093fad7eefa4ee5faf83f346dc516c808cf983791ac159313a7e85a3e53`

## Interpretation

The controlled frozen baseline passes the selected IPQ-E adapter, transport, extraction and Gateway commitment scenarios. The strongest justified statement is that the frozen implementations reproduce their bounded source-side and Gateway commitment invariants under deterministic controlled fixtures.

This result does **not** upgrade source records into source truth, establish source completeness, or demonstrate continuous live connectivity to third-party production services. A successful adapter collection remains a source-side operational observation until ETS commits the resulting candidate through its evidence path; source health and ETS cryptographic verification remain distinct states.

## Final exact-head qualification

Adding this result record changes the harness head, so all earlier general CI/security/formal results are stale for merge purposes. The final #346 head must rerun the detached IPQ-E workflow plus repository CI, Security Audit, CodeQL, Formal Specs, Benchmarks, Apalache and Lean, then receive fresh independent review. Final run identifiers can be attached to #345/#322 without changing the frozen SUT or rewriting this initial evidence result.

## Nonclaims

No claim is made here regarding production credentials, live SaaS availability, source truth/completeness, legal admissibility, regulatory compliance, high availability, hardware attestation, production GA, or later post-baseline connector behavior.
