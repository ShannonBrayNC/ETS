# WP2 — EXP-001 Packet Freeze Reconciliation

**Status:** prospective pre-execution reconciliation  
**Experiment:** EXP-001  
**Execution state:** NOT EXECUTED  
**Parent baseline:** `4f34bac7679dbad90727fed5208afbcb012bc256`

## Purpose

Resolve the pre-execution discrepancy between the committed deterministic packet renderer and the earlier predeclared packet SHA-256 manifest without hiding, rewriting, or treating the discrepancy as experimental evidence.

## Integrity boundary

No evaluator has been exposed to EXP-001 packets and no participant outcome data exist. Therefore a prospective correction remains permissible provided the failed freeze comparison remains preserved and every correction is documented before evaluator exposure.

This work package MUST NOT:

- execute EXP-001;
- recruit evaluators;
- score responses;
- inspect outcome data;
- promote EA-C001 or EA-C002;
- change the frozen scenario facts merely to make hashes match;
- silently replace the discrepancy record.

## Authoritative-source decision rule

The candidate authoritative packet set SHALL be the byte-for-byte output produced by the committed `packet_source.json` and `generate_packets.py` at the WP2 baseline, provided all of the following hold:

1. the renderer is deterministic;
2. it generates exactly 36 packets;
3. the source contains the frozen 12 scenarios;
4. the A/B/C to M/R/K mapping remains unchanged;
5. the rendered packets preserve the substantive fact inventory;
6. an independent fact-equivalence review can certify all 12 triplets;
7. a second clean regeneration reproduces the same hashes.

If any requirement fails, the source/renderer is not yet authoritative and the discrepancy remains unresolved.

## Reconciliation procedure

1. Preserve `EXP-001_PACKET_FREEZE_DISCREPANCY.md` and the old expected manifest as historical evidence of the failed freeze.
2. Run the deterministic renderer in a clean environment.
3. Capture the generated 36 packet hashes.
4. Run the renderer a second time from the same commit and require identical hashes.
5. Compare packet facts against the frozen scenario/fact inventory.
6. Commit the 36 rendered packets only after the repeated-render check passes.
7. Commit a new authoritative SHA-256 manifest with an explicit supersession note; do not erase the historical manifest.
8. Update `EXP-001_ARTIFACT_MANIFEST.md` with exact packet and assignment hashes.
9. Obtain independent fact-equivalence certification for all 12 triplets.
10. Keep evaluator recruitment blocked until the governing institution supplies the applicable human-subjects determination.

## Supersession semantics

The earlier `rendered_sha256.expected.json` remains a historical pre-execution artifact showing an unsuccessful freeze attempt. It SHALL NOT be deleted or retroactively described as correct.

A corrected manifest, if established prospectively, SHALL use a new filename and state:

- the baseline commit;
- the renderer/source blob identities;
- the deterministic seed and opaque mapping;
- the reason for supersession;
- the 36 packet SHA-256 values;
- the repeated-render verification result;
- the date and commit of the corrected freeze.

## Current state

- WP1 prior-art qualification: merged.
- EXP-001: NOT EXECUTED.
- Old expected packet manifest: known discrepant; retained.
- Assignment plan: prospectively frozen.
- Human evaluator recruitment: blocked.
- Corrected packet freeze: pending deterministic clean-run reconciliation.

No scientific claim changes result from this work package.