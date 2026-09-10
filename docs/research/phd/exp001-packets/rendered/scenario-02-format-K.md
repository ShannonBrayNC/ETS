# Scenario 02 — Format K

## Evidence representation

**Bounded evidence representation**

The same factual record is represented as evidence claims with explicit verification boundaries:
- E01 [evidenced fact]: Procurement policy requires approvals from Procurement and Finance for purchases over $100,000.
- E02 [evidenced fact]: A $148,000 purchase order was issued.
- E03 [evidenced fact]: Procurement approval evidence is present and valid.
- E04 [evidenced fact]: Finance approval evidence is absent from the provided evidence package.
- E05 [evidenced fact]: The capture system reports 92% ingestion availability during the relevant two-hour interval because one connector was degraded.
- E06 [evidenced fact]: The purchase order was accepted by the vendor.
- E07 [evidenced fact]: No evidence establishes whether Finance approved through another channel.

**Boundary annotations**
- Absence from the package is separate from absence of the underlying Finance approval.
- Capture capability was degraded during the interval.
- Vendor acceptance does not establish full procurement compliance.

**Strongest bounded conclusion encoded by the representation**
- The package lacks Finance approval, but incomplete capture prevents concluding that Finance approval did not occur. The purchase order was issued and accepted by the vendor.

## Reconstruction questions

1. What events or states are directly supported by the evidence?
2. What conclusions are inferred rather than directly observed?
3. Which actor/action possessed valid standing at the relevant time, if established?
4. What action was requested, what action was executed, and what consequence/result was actually observed?
5. What material facts remain unknown, unavailable, contradictory, stale, or unverified?
6. What is the strongest defensible overall conclusion without exceeding the evidence?

---
Do not infer facts that are not represented. Record uncertainty explicitly when the evidence does not resolve a question.
