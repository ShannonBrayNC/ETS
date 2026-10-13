# P0 Step 4 handoff

Step 4 is the Evidence Object / consequence-custody closure for the frozen Agent 365 + M365 + Ranger R0 demonstration.

Implementation:

- `ets/ranger/agent365_r0_evidence.py`
- `tests/test_agent365_r0_evidence.py`
- `docs/demos/AGENT365_R0_CONSEQUENCE_CLOSURE.md`

The closure retains and verifies the SharePoint authorization, all three Gateway envelopes, the Gateway robot command, the Ranger motion and stop directives, and all seven Ranger boundary records. It then projects the verified facts into the existing Ranger Decision Event and ETS Evidence Object v1 path.

The decisive invariant remains:

```text
STOP_ACTUATED != proof chassis stopped
RESULT_OBSERVED from an independent result sensor -> support for the stopped-state claim
```

The frozen P0 record set still does not contain a separate actuator acknowledgement or independent actuator-response measurement. Those states remain `NOT_OBSERVED`; Step 4 does not synthesize them.

A verified closure can update the Microsoft-side SharePoint mission with `EvidenceObjectId`, `EvidenceBundleRef`, and the terminal mission status without altering the original authorization-material commitment.
