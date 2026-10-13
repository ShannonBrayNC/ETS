# Agent 365 + Ranger R0 — Step 4 consequence evidence closure

**Status:** executable P0 evidence contract; not a physical safety certification

Step 4 closes the frozen Ranger R0 demonstration into the existing ETS Ranger Decision Event and Evidence Object v1 paths. It does not broaden the motion scenario. The only physical action remains the Step 3 bounded forward-motion contract.

The closure proves that the retained records form one internally consistent evidentiary path:

```text
SharePoint authorization
        ↓ authorization-material commitment
Gateway ingress
        ↓ digest / parent linkage
Gateway authorization decision
        ↓ digest / parent linkage
Gateway robot-command egress
        ↓ exact command payload commitment
Ranger RECEIVED
        ↓
Ranger AUTHORIZED
        ↓
Ranger MOTION_STARTED          independent motion observation
        ↓
Ranger STOP_CONDITION_OBSERVED independent stop-condition observation
        ↓
Ranger STOP_DECIDED
        ↓
Ranger STOP_ACTUATED           zero-motion command boundary
        ↓
Ranger RESULT_OBSERVED         independent stopped-state observation
        ↓
Ranger Decision Event
        ↓
ETS Evidence Object v1
        ↓
reverse verifier
        ↓
SharePoint completion references
```

## Why Step 4 exists

Step 3 deliberately separated command receipt, policy authorization, physical motion observation, stop decision, stop actuation, and resulting-state observation. Step 4 must preserve those distinctions when the records enter the ETS evidence plane.

The closure therefore does **not** translate `STOP_ACTUATED` into a claim that the chassis stopped. The stopped-state claim is supported only by the final `RESULT_OBSERVED` record, whose source class is `independent_result_sensor` and whose observer identity must differ from the motion controller identity.

## Retained source bundle

`build_agent365_r0_consequence_closure(...)` retains the canonical bytes for fourteen source artifacts:

1. authorized SharePoint mission artifact;
2. Gateway ingress envelope;
3. Gateway authorization-decision envelope;
4. Gateway egress envelope;
5. Gateway Ranger command;
6. Ranger motion directive;
7. Ranger stop directive;
8. `RECEIVED` boundary record;
9. `AUTHORIZED` boundary record;
10. `MOTION_STARTED` boundary record;
11. `STOP_CONDITION_OBSERVED` boundary record;
12. `STOP_DECIDED` boundary record;
13. `STOP_ACTUATED` boundary record; and
14. `RESULT_OBSERVED` boundary record.

Each source artifact receives a SHA-256 reference in the Ranger Decision Event. `verify_ranger_source_evidence(...)` can therefore recompute every retained source digest rather than trusting the projection.

## Semantic verification before projection

The closure fails closed unless all of the following are true:

- the SharePoint mission is `AUTHORIZED` and still inside the pre-completion state boundary;
- the Gateway command carries the exact SharePoint authorization-material commitment;
- the Gateway command policy and command parameters match the authorized SharePoint artifact;
- the dispatch is the first execution-bearing delivery, not a transport retry;
- Gateway ingress → authorization decision → egress parent and digest links verify;
- Gateway egress commits to the exact Ranger command payload;
- the Ranger receipt is anchored to that Gateway egress event and digest;
- the seven Ranger records occur exactly once and in the frozen order;
- every Ranger record retains the same `mission_id` and authorization-artifact reference;
- every Ranger record chains to the immediately preceding record by event ID and canonical digest;
- the motion directive is bound to the original Gateway delivery and authorized motion limits;
- the stop directive is a zero-motion command from the same controller/vehicle identity;
- the stop directive reason matches the `STOP_DECIDED` and `STOP_ACTUATED` records;
- the final outcome is `STOP_CONFIRMED`;
- the final observer is not the motion controller; and
- the final source class is `independent_result_sensor`.

A missing record, cross-mission splice, changed digest, changed command, changed policy, retry substitution, or result asserted by the controller causes closure to fail.

## Decision Event projection

The generated Ranger Decision Event records affirmative `KNOWN` claims for the facts actually supported by the source records:

- mission authorized;
- Gateway dispatch accepted;
- motion independently observed;
- stop condition independently observed;
- stop decision selected;
- zero-motion stop command issued; and
- stopped state independently observed.

Only claims supported by retained source references are projected into Evidence Object v1. The full Ranger Decision Event remains authoritative in the namespaced Ranger extension.

## Actuator epistemic boundary

The frozen seven-stage P0 contract contains no separate actuator acknowledgement signal and no controller-independent actuator-response measurement. Step 4 preserves that absence:

```text
selected_action          KNOWN
issued_command           KNOWN
command_acknowledgement  NOT_OBSERVED
actuator_response        NOT_OBSERVED
observed_consequence     KNOWN / independently supported
```

This is intentional. A downstream verifier should be able to distinguish:

> “A stop command was issued and an independent sensor later observed the stopped state.”

from the stronger statement:

> “The actuator acknowledged the stop command and an independent actuator sensor proved the actuator response.”

The second statement is outside the frozen P0 record set and is not manufactured by Step 4.

Because the pre-existing generic Ranger consequence verifier requires the intermediate actuator acknowledgement/response stages for an overall `SUPPORTED` causal path, it conservatively reports `NOT_OBSERVED` for the aggregate actuation path. The Step 4 verifier separately verifies the frozen seven-stage contract and the independent resulting-state evidence. This difference is a feature of the epistemic model, not a test exception.

## Reverse verification

`verify_agent365_r0_consequence_closure(...)` does not trust the builder's live objects. It:

1. verifies the Ranger Decision Event digest and Evidence Object integrity binding;
2. recomputes the outer Evidence Object hash;
3. verifies every retained source-artifact digest;
4. reparses the canonical retained artifacts;
5. re-runs SharePoint → Gateway → Ranger semantic linkage checks;
6. confirms the Gateway egress anchor embedded in the closure summary;
7. confirms controller and result-observer identities from retained source records; and
8. confirms that the projected observed consequence is supported by the final independent measurement reference.

An optional trusted Ranger public key can additionally require the closure Decision Event signature to verify.

## Closing the Microsoft-side mission

After reverse verification succeeds, `complete_sharepoint_mission_from_closure(...)` produces the completed SharePoint mission artifact while proving that the original authorization-material digest did not change.

For the obstacle-stop demonstration, the status becomes:

```text
COMPLETED_OBSTACLE_STOP
```

and the mission receives:

```text
EvidenceObjectId
EvidenceBundleRef
```

`sharepoint_completion_patch_body(...)` returns the minimal Microsoft Graph list-item field patch for those completion fields.

Stop reasons map to SharePoint completion states as follows:

| R0 stop reason | SharePoint status |
| --- | --- |
| `obstacle_within_stop_distance` | `COMPLETED_OBSTACLE_STOP` |
| `max_distance_reached` | `COMPLETED_STOP_POINT` |
| `max_duration_reached` | `COMPLETED_STOP_POINT` |
| `hardware_estop` | `ABORTED_ESTOP` |
| `policy_abort` | `ABORTED_POLICY` |

## Test coverage

`tests/test_agent365_r0_evidence.py` exercises the real Step 1 authorization model, Step 2 Gateway guard, and Step 3 Ranger boundary before Step 4 projection. The tests verify:

- complete SharePoint → Gateway → Ranger → Evidence Object closure;
- all fourteen retained source artifacts;
- independent result support without promoting stop command to physical proof;
- SharePoint completion with unchanged authorization material;
- failure on a missing Ranger stage; and
- reverse-verifier failure when retained source bytes are tampered.

## P0 claim boundary

A successful Step 4 verification supports this statement:

> The supplied frozen R0 evidence bundle has a valid authorization/dispatch/boundary chain, and its independent result record supports that the Ranger was observed stopped within the authorized distance boundary.

It does **not** by itself prove that every real-world event was captured, that the sensors were physically truthful, that an unobserved actuator acknowledgement occurred, or that the system is functionally safe or certified.

That separation is the point of the Evidence Architecture: authority, command, observation, consequence, and evidentiary confidence remain distinct rather than collapsing into one success flag.
