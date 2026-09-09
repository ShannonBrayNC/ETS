# EXP-001 Packet Freeze Discrepancy Record

**Status:** pre-execution integrity finding  
**Date:** 2026-09-09  
**Experiment:** EXP-001  
**Evaluator data observed:** NO  
**Execution state:** NOT EXECUTED

## Finding

A regeneration check performed before materializing the 36 evaluator packets found that packet content produced from the currently committed `packet_source.json` and `generate_packets.py` does not reproduce the SHA-256 values recorded in `rendered_sha256.expected.json`.

This is treated as a preregistration/control-artifact inconsistency. It is **not** treated as an experimental result and it does not support or weaken EA-C001 or EA-C002.

## Research-integrity response

The existing expected-hash manifest SHALL NOT be silently replaced.

Before any evaluator exposure:

1. identify whether the divergence arose from source drift, renderer drift, newline/encoding differences, or an incorrectly generated expected manifest;
2. run the committed renderer in a clean environment directly against the committed source;
3. compare all 36 generated files byte-for-byte with the expected manifest;
4. preserve the failing comparison artifact;
5. if the committed source/renderer are confirmed authoritative, create a dated pre-execution amendment that supersedes the incorrect expected manifest;
6. generate and commit a replacement manifest from the authoritative clean render;
7. independently verify the replacement manifest before evaluator exposure.

## Confirmatory boundary

Because no evaluator data has been collected, correcting a demonstrably erroneous pre-execution hash manifest can remain prospective if the correction is fully documented before exposure.

No packet is considered confirmatory-frozen until its bytes reproduce the authoritative manifest in a clean verification run.

## Current gate

**BLOCKED: PACKET HASH FREEZE NOT YET VALIDATED.**

EXP-001 remains NOT EXECUTED and no evaluator recruitment or exposure is authorized by this repository state.
