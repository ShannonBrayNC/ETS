# Agent 365 + Ranger R0 end-to-end qualification

This qualification is the P0 software gate for the frozen four-week demonstration.
It proves that one bounded mission can traverse the ETS contracts and still be reconstructed
from durable retained evidence after a restart boundary.

## Qualified path

The harness exercises this exact sequence:

1. Create the frozen SharePoint-style mission artifact with one `mission_id`.
2. Authorize it under `r0-forward-stop-policy.v1`.
3. Bind the authorization material into the Gateway request.
4. Dispatch the bounded R0 command through the durable Gateway replay ledger.
5. Record the seven frozen Ranger R0 boundary stages:
   - received;
   - authorized;
   - motion started;
   - stop condition observed;
   - stop decided;
   - stop actuated;
   - result observed.
6. Build and verify the Evidence Object v1 consequence closure.
7. Promote the retained closure to Evidence Object v2 with the canonical mission binding.
8. Persist the complete verified bundle and exact retained source bytes in the durable mission store.
9. Close the store and reopen it, so reconstruction depends only on retained state.
10. Rebuild the verified `mission_id` index.
11. Query the same mission through the read-only Agent 365/R0 HTTP contract in the qualification test.
12. Confirm that decision-event, Evidence Object v1, Evidence Object v2, and physical-result fields are identical across the restart boundary.

The generated report is written to:

`<workdir>/<mission_id>/qualification-report.json`

The run directory also retains the Gateway ledger, Ranger ledger, and mission-bundle SQLite database.

## Run locally

```bash
python -m ets.demos.agent365_r0_qualification \
  --workdir qualification-output/agent365-r0
```

Optionally pin the mission identifier:

```bash
python -m ets.demos.agent365_r0_qualification \
  --workdir qualification-output/agent365-r0 \
  --mission-id 4db39caa-3794-47f7-9bf0-bf5cf79fb912
```

The process exits non-zero if any semantic, evidence, durability, or reconstruction invariant fails.

## What a green result means

A green qualification supports these bounded statements:

- the same explicit `mission_id` survives authorization, Gateway dispatch, Ranger boundary evidence, Evidence Object v1, Evidence Object v2, durable retention, restart, and query reconstruction;
- the retained Evidence Object v2 bundle verifies after being loaded from durable custody;
- an independent result observer supports the frozen `STOP_CONFIRMED` result;
- exact retained source bytes survive the durable store;
- the read-side mission manifest resolves to the same decision-event and Evidence Object commitments created before restart.

It does **not** convert integrity or correlation into unbounded physical truth.  It also does not claim that the reference software observations are live Agent 365 telemetry or measurements from the physical robot.

## Relationship to the live demo

This gate deliberately fixes the software semantics before live integration.  The next P0 step replaces the reference Microsoft-side inputs and reference Ranger sensor observations with real acquisition while preserving the same contracts:

`Agent 365 / SharePoint -> ETS Gateway -> physical R0 -> independent observer -> Evidence Object v2 -> durable mission API`

For Microsoft integration, the live path must preserve the exact `mission_id` rather than derive a new correlation value at each subsystem.

For the physical R0 run, controller-issued stop state and independently observed stopped state remain separate evidence propositions.  A successful command or tool call is not treated as proof of the external result.
