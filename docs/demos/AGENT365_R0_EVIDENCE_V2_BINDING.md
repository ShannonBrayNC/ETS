# Agent 365 + Ranger R0 P0 — Evidence Object v2 mission binding

Status: P0 implementation Step 5  
Scope: frozen `agent365-r0-forward-stop-v1` demonstration only

## Purpose

Step 4 closes the Microsoft authorization, Gateway dispatch, Ranger execution boundary, and independently observed physical result into the existing Ranger Decision Event and Evidence Object v1 path. Step 5 does **not** replace that evidence. It performs the additive Evidence Object v2 promotion required by the frozen mission contract.

The v2 object gives the demonstration a canonical mission context binding while preserving the original v1 object and its hash as historical source evidence.

## Required mission binding

Every promoted object carries exactly one context binding:

```json
{
  "binding_type": "context",
  "contract_id": "lantern.demo.agent365-r0.mission.v1",
  "subject_ref": "mission:<mission_id>"
}
```

The same mission is exposed for query/index use through:

```json
{
  "extensions": {
    "lantern.demo": {
      "mission_id": "<mission_id>",
      "scenario_id": "agent365-r0-forward-stop-v1"
    }
  }
}
```

A mismatch between the context binding and the extension is a verification failure.

## v1 preservation and commitment

Evidence Object v2 is additive. The Step 4 Evidence Object v1 is never rewritten.

The v2 object contains a `provenance` binding to the v1 object and commits to the canonical v1 object hash. The v1 object is also carried as `proof_material` for a portable demonstration package.

Because Evidence Object v2 intentionally excludes `proof_material` from its canonical identity preimage, the verifier independently hashes the attached v1 object and compares it with the provenance commitment. Altering proof material therefore does not alter the v2 identity hash, but it does make verification fail.

## Ranger Decision Event binding

The v2 object also contains an `event` binding to the retained Ranger Decision Event. The binding commits to the event's existing `sha256:` digest without creating a second event identity.

This preserves the chain:

```text
mission_id
  -> SharePoint authorization
  -> Gateway authorization/dispatch
  -> Ranger receipt and motion boundary
  -> independent RESULT_OBSERVED
  -> Ranger Decision Event
  -> Evidence Object v1
  -> Evidence Object v2 context/provenance/event bindings
```

## Verification boundary

Successful Step 5 verification establishes that:

- the Step 4 consequence closure still verifies;
- the final physical stopped-state claim remains supported by the independent result observation;
- the v2 canonical identity hash is correct;
- exactly one frozen P0 mission context binding exists;
- the `lantern.demo` mission/scenario extension agrees with that binding;
- the v1 provenance binding points to and commits to the retained Evidence Object v1;
- the Ranger event binding points to and commits to the retained Decision Event;
- attached v1 proof material hashes to the committed v1 object;
- the compatibility extension agrees with the retained Step 4 bundle.

It does **not** claim that cryptographic integrity, correlation, or a verified sensor report establishes unbounded physical truth. The Step 4 epistemic boundary remains unchanged.

## Failure conditions

The Step 5 verifier fails closed for at least:

- changed v2 canonical identity material;
- missing or duplicated P0 mission context bindings;
- mission/scenario extension drift;
- v1 provenance reference or commitment drift;
- Ranger Decision Event reference or commitment drift;
- malformed or altered attached v1 proof material;
- compatibility metadata that disagrees with the retained Step 4 closure;
- any Step 4 closure that no longer verifies.

## Tests

`tests/test_agent365_r0_evidence_v2.py` covers:

- successful v2 promotion and verification;
- exact mission context and query-extension agreement;
- v1 provenance commitment;
- proof-material exclusion from the v2 identity preimage;
- proof-material tamper detection despite unchanged v2 identity;
- mission extension drift rejection;
- v1 commitment drift rejection.

## Next P0 boundary

After this binding is green and merged, the next implementation increment is **mission reconstruction by `mission_id`**. The verifier must query the mission-scoped package and reconstruct the ordered authorization -> dispatch -> physical consequence -> v1 -> v2 chain without relying on display labels or inferred identifiers.
