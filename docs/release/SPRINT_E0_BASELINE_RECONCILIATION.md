# Sprint E0 Baseline Reconciliation

Status: pending human merge gates
Date: 2026-08-01

## Authoritative baseline rule

`main` is the only authoritative product baseline. The edge MVP baseline becomes effective only after the alpha-freeze issue #157 is complete and the exact validated merged-main commit is recorded.

## Branch and PR disposition

| Item | Disposition | Rationale |
|---|---|---|
| PR #154 | Merged baseline dependency | Runtime profile guard and RFC 6962 vector correction are already in `main`. |
| PR #156 | Required before alpha freeze; retain and promote through normal review | Adds independent dependency, secret-scan, Explorer, and Docker-federation gates. It remains draft and requires independent review before merge. |
| Issue #157 | Required release-freeze gate | Must reconcile release documents, generated OpenAPI, exact-head validation, and the no-tag-before-approval decision after #156 merges. |
| PR #160 | Governance dependency; retain separately | Defines protocol governance and publication controls. It must not be conflated with edge runtime implementation. |
| PR #159 | Additive future semantic model; not an MVP prerequisite | Evidence Object v1 may continue without replacing the alpha event API, Merkle semantics, or historical logs. |
| PR #153 | Superseded by PR #160 and the accepted product/governance taxonomy | Broad strategy documentation is retained in history; authoritative governance belongs in the reviewed governance artifacts. |
| PR #136 | Superseded for MVP sequencing | Protocol-adoption roadmap is not the technical edge baseline; useful material may be harvested after governance approval. |
| PR #133 | Superseded as a single broad public-release change set | Its public-release, lab, research, and implementation-guide changes must be split or harvested through scoped reviewed PRs. |
| PR #124 | Deferred and not part of the MVP baseline | Azure-hosted signing and telemetry are hosted-product work. Reusable signer interfaces may be harvested through a narrow future PR. |
| PR #138 | Deferred and not part of the MVP baseline | Azure tenant configuration is a cloud convenience path, not the initial Ubuntu edge-appliance baseline. |
| Edge issues #140–#145 | Retained as parent outcomes | Execution should reference the frozen MVP contract, edge profile, capture schema, and ADR in this Sprint E0 change set. |

## Critical-runtime inclusion check

The current MVP baseline requires the following before edge implementation branches:

- runtime profile safety and RFC 6962 vectors from merged PR #154;
- security-audit and Docker-federation gates from PR #156 after review and merge;
- final release documents, generated OpenAPI, and exact merged-main validation from #157;
- edge MVP contract, protocol profile, capture-envelope schema, and ADR from this Sprint E0 PR.

No hosted Azure branch, Evidence Object branch, public-release mega-branch, or strategy-document branch is authoritative for the initial edge runtime.

## Merge order

1. Obtain independent review and merge PR #156.
2. Complete #157 on a fresh branch from updated `main`; merge after all required validation and independent approval.
3. Rebase this Sprint E0 branch on the resulting frozen `main` if necessary.
4. Obtain protocol/security review and merge the Sprint E0 contract PR.
5. Record the resulting merged-main commit as the starting point for Sprint E1.

## Exit determination

Sprint E0 is technically specified when this document and its associated contract/profile/schema/ADR are approved. Sprint E0 is operationally complete only after the merge order above finishes and one exact merged-main commit is recorded. No tag, production deployment, or edge implementation may bypass the required human approvals.
