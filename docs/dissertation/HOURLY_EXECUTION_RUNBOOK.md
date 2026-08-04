# ETS Dissertation Hourly Execution Runbook

Program issue: `#120`  
Queue: `config/dissertation-work-queue.json`  
Requirements: `docs/requirements/ETS_DISSERTATION_PUBLICATION_REQUIREMENTS.md`

## Purpose

This runbook governs hourly continuation of the ETS dissertation program. The
hourly automation performs scholarly and technical work through GitHub; the
GitHub Actions control workflow validates the queue and reports the next item.

The two mechanisms have different responsibilities:

- The hourly work automation may research, edit, test, and create or update a pull
  request for one selected queue item.
- The GitHub Actions workflow is read-only. It validates configuration and publishes
  the deterministic next-work summary. It does not claim task completion.

## Focus Mode

While `program.mode` is `dissertation_only`:

- no other autonomous ETS feature sprint may be selected;
- unrelated repositories and image/content jobs remain paused;
- pull-request CI, formal verification, benchmarks, security checks, and manuscript
  validation remain allowed because they produce or validate dissertation evidence;
- emergency security remediation may interrupt the queue only through an explicit
  human decision recorded in issue `#120`.

## One-Pass Procedure

Each hourly pass MUST perform this sequence:

1. Fetch current `main`, issue `#120`, referenced dependency issues, and open PRs.
2. Read and validate the queue:

   ```text
   python scripts/dissertation_queue.py validate
   python scripts/dissertation_queue.py next --json
   ```

3. Check whether the selected task already has an open branch, PR, issue comment,
   artifact, or materially equivalent output.
4. If duplicate work exists, continue or review it rather than starting over.
5. Confirm the task is automation-eligible and does not require approval for the
   proposed action.
6. Set only that task to `in_progress` in the working change and record the branch or
   PR in `completion_evidence` only as work evidence, not completion evidence.
7. Implement the smallest complete output that satisfies all acceptance criteria.
8. Prefer primary and authoritative sources; verify every new citation.
9. Run every validation listed on the task plus the queue tests.
10. Update claim status, limitations, citations, and artifact indexes affected by the
    work. Do not silently leave a contradictory document behind.
11. Mark the task `completed` only when acceptance criteria pass and
    `completion_evidence` contains stable paths, commit SHA, test result, and PR or
    workflow reference.
12. Promote at most one newly unblocked planned task to `ready`.
13. Update issue `#120` with a concise pass record and update or open the task PR.
14. Stop. Do not process a second task in the same run.

## Pass Record

Every pass comment on issue `#120` SHOULD contain:

- pass timestamp and queue SHA;
- selected task ID and title;
- anti-duplication result;
- files/artifacts changed;
- sources added or reviewed;
- validation commands and results;
- claim-status changes;
- PR and workflow links;
- next eligible or blocked task;
- human action required, if any.

## Status Transitions

Allowed normal transitions:

```text
planned -> ready -> in_progress -> human_review -> completed
planned -> ready -> in_progress -> completed
planned/ready/in_progress/human_review -> blocked
blocked -> ready
planned/ready/blocked -> cancelled
```

Rules:

- `completed` requires non-empty completion evidence.
- `human_review` is not equivalent to approval.
- A task with `approval_required = true` remains blocked or in human review until an
  authorized person records the decision.
- Failed, missing, timed-out, or expired validation evidence blocks claims that depend
  on it but does not justify falsifying a passing result.
- If the task grows beyond one bounded pass, preserve work in a PR, keep it
  `in_progress`, and continue the same task on the next pass.

## Branch and Pull-Request Policy

- Use `codex/dissertation-<lowercase-task-id>` for a new task branch.
- Reuse the existing branch and PR for an in-progress task.
- One PR SHOULD contain one queue task unless inseparable validation corrections are
  required.
- Link issue `#120` and all task issue references.
- Documentation and research-only PRs MAY merge after required checks pass when no
  human or publication gate applies.
- Runtime, security, formal-model semantic, IP-sensitive, or approval-gated changes
  MUST remain reviewable and MUST NOT auto-merge solely because CI is green.
- No automation may publish a preprint, submit to a venue, create a public release,
  schedule a defense, approve authorship, or deposit a dissertation.

## Source and Citation Procedure

For each new material source:

1. Prefer the primary paper, standard, RFC, government publication, official tool
   documentation, or institutional policy.
2. Resolve title, author/organization, year/date, venue/publisher, DOI or stable URL,
   and source type.
3. Record the accessed date for web sources.
4. State which claim the source supports, contextualizes, weakly supports, or
   contradicts.
5. Record limitations and avoid copying source language beyond quotation limits.
6. Add or update the bibliography and source-quality ledger.

If a source cannot be verified, log it as a candidate and do not cite it as evidence.

## Formal and Empirical Evidence Procedure

Before changing a formal or empirical claim, capture:

- exact commit and workflow/run;
- tool version and command;
- model/configuration/bounds or experiment manifest;
- seed, dataset, repetitions, and hardware where applicable;
- result and exit status;
- logs/artifacts and checksum;
- timeout, skip, or unsupported constructs;
- what the result proves and does not prove.

Model checking, symbolic checking, mechanized proof, proof sketch, unit test, and
simulation are different evidence categories and MUST remain distinct.

## Blocking Conditions

Stop the pass and report a blocker when:

- GitHub access or required source access is unavailable;
- another pass or PR owns the same task;
- the selected work requires advisor, committee, institutional, participant, IP,
  legal, security-owner, or publication approval;
- a required artifact contains secrets or controlled data;
- the task requires paid infrastructure or external publication not already approved;
- the repository state contradicts the queue and cannot be safely reconciled;
- no task is ready and no planned task is eligible for promotion.

Do not select unrelated work merely to keep the automation busy.

## Recovery

If a pass fails:

1. leave the selected task `in_progress` or `blocked`;
2. preserve reproducible diagnostics without secrets;
3. link the failed workflow or PR;
4. record the smallest next recovery action;
5. retry the same task on the next hourly pass unless a higher-priority human decision
   changes the queue.

If queue validation fails, queue repair becomes the sole allowed action for that pass.

## Completion Boundary

The automation stops selecting work when no automation-eligible task is ready. The
program remains open while human and institutional gates are incomplete. Only verified
advisor, committee, Graduate Education, defense, IP/copyright, and deposit records can
close the program.
