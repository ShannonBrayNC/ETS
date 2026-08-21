# ETS Black Box Test Plan

## Software qualification

Primary suite: `tests/unit/test_black_box.py`.

The suite must prove:

1. **Rolling retention** — only the configured newest pre-trigger frames remain during ordinary capture.
2. **Trigger freeze / auto seal** — frozen pre-window survives, exact post count is captured, and segment
   seals at the defined boundary.
3. **Tamper and wrong-key rejection** — changed frame digest or unrelated public key fails verification.
4. **Digest-only schema** — raw extra payload fields fail strict validation.
5. **Ordering and revalidation** — per-boot monotonic order is strict and unchecked copied models are
   revalidated before signing.
6. **Size bound** — oversized canonical observation fails before sequence/state advances.
7. **Power-loss-imminent seal** — a partial post-window can be explicitly sealed and verified.
8. **Restart recovery** — SQLite persists active trigger, restart with a higher boot counter continues the
   post-window, and the final segment spans both boots without a gap.
9. **Boot anti-rollback** — boot-ID substitution without counter advance and counter rollback fail closed.
10. **Production floor** — both reference stores are rejected under `require_production_backend=True`.
11. **Core minimization** — private frame attributes and trigger free-text are absent from Core projection,
    while Core content hash equals segment hash.
12. **Gap detection** — removing an interior frame makes segment verification fail.

## Repository qualification

The Black Box branch must pass the existing repository gates, including applicable Ruff, strict mypy,
full pytest, dependency/security audit, secret scan, CodeQL, architecture/formal checks, and existing
hosted/Edge/Gateway regression workflows. No gate should be weakened for this feature.

## Physical qualification

Software tests are necessary but insufficient. A physical appliance must additionally execute:

- **TPM key custody:** prove supported interfaces cannot export production private key; power-cycle and
  re-attest identity.
- **Secure/measured boot:** approved measurement passes; modified boot/firmware fails or quarantines;
  protected recovery restores approved state.
- **Anti-rollback:** newer approved generation blocks prohibited old firmware/software.
- **Destructive power-cut matrix:** randomized cuts during frame commit, trigger activation, post capture,
  segment seal, ring prune, and export acknowledgement. No acknowledged frame within the qualified PLP
  contract may disappear or fork the chain.
- **Hold-up margin:** measure worst-case brownout-to-durable-seal time at low/high temperature, near-full
  media, media garbage collection, and max incident size with engineered reserve margin.
- **Endurance/thermal soak:** sustained maximum write rate through target lifetime workload while
  monitoring latency tail, throttling, media errors, temperature, and integrity.
- **Tamper input:** enclosure/open/debug events produce required trigger/evidence/fleet behavior.
- **Sealed overwrite resistance:** attempt overwrite/delete through app admin, OS root, maintenance, and
  storage-management interfaces; require prevention or independent detection matching product claim.
- **Network isolation:** no Internet-facing management, authenticated device/fleet paths, revocation and
  quarantine, capture continuity offline.
- **Time degradation:** remove trusted time, induce drift/offset/source changes, and verify local sequence
  remains sound while clock-quality evidence degrades.
- **Export recovery:** block Gateway/Core/Vault, accumulate sealed incidents, restore connectivity, and
  prove ordered/idempotent export without changing segment identity.
- **Key lifecycle:** enrollment, rotation, compromise/revocation, replacement, decommission, historical
  verification.
- **Sanitization:** execute approved NIST SP 800-88 Rev. 2 procedure and retain sanitization evidence
  outside the sanitized unit.
- **Domain survivability:** any crash/fire/water/vibration/EMI claim requires the applicable independent
  certification tests on the complete enclosure/storage/power assembly.

## Exit criteria

**Software reference:** Black Box tests and all existing ETS CI/security/formal gates green; no new
secrets; docs/threat model present; Core projection minimized; reference stores remain non-production.

**Physical pilot:** hardware identity, measured boot, PLP/power, tamper, endurance, fleet, export, and
recovery gates pass for the selected hardware, with explicit non-production exceptions documented.

**Production:** all physical gates pass, independent evidence supports every production backend capability,
and applicable deployment-domain environmental/regulatory qualification is complete.
