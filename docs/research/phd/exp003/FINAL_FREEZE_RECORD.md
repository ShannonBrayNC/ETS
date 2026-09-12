# EXP-003 Final Pre-Execution Freeze Record

**Status:** BYTE FREEZE COMPLETE — CONFIRMATORY EXECUTION NOT AUTHORIZED  
**Frozen source commit:** `d81a210120023be4edfb50bdf5566608ac4bf3c9`  
**Freeze-control PR:** #727  
**Freeze-control merge commit:** `35ddb6ca64fcb6a3eeeba7799814c36de48ff9ea`  
**Successful freeze workflow run:** `34713151692` (`EXP-003 Freeze Hashes`, run 3)  
**Workflow head SHA:** `6f3defbea5cc11e06a6a90c098278f0c072266bb`  
**Workflow test-merge commit reported by hash utility:** `4047ca5d2ca4e8eb7c75e5dc6666a4730108b033`  
**Artifact ID:** `10303439692`  
**Artifact digest:** `sha256:6734ff13c254b0aab11d99f5ee07008b923c358cd8a219c3d466474fb0d016ec`  
**Recorded:** 2026-09-12

## Interpretation

The freeze workflow verified that every frozen EXP-003 semantic, executable, and formal artifact was byte-identical to the frozen source commit before hashing. The workflow ran from a clean checkout and reported `working_tree_clean=true`.

PR #727 added only freeze/review control material. It did not alter the frozen EXP-003 source artifacts. The frozen artifact bytes therefore remain those introduced by PR #725 at source commit `d81a210120023be4edfb50bdf5566608ac4bf3c9` and carried unchanged through the #727 merge.

## Hash environment

- Python: `3.12.14`
- Platform: `Linux-6.17.0-1022-azure-x86_64-with-glibc2.39`
- Working tree: clean
- Hash algorithm: SHA-256

## Frozen artifact SHA-256 values

| Artifact | SHA-256 |
| --- | --- |
| `BASELINE_PROFILE.json` | `8b729072fa2472662e9e3b43e092b5982b6534f53e07310a95e4cce471120664` |
| `CONSEQUENCE_MODEL.json` | `1d8069797da31cc5bb5ea57791d79cf6d399f40577595b06a89f5fc9f4763518` |
| `EPISTEMIC_STATES.json` | `eb0336df719e3c02ac989b81a932cbd67af52e1e5865d73afe12fefc923a0401` |
| `EXP003NonCollapse.tla` | `0b61ebcf7a7a8de25e665b7b2b79f2915dfa656a88cf8dfed8a32d57a9133af9` |
| `FACT_GRAMMAR.json` | `586c791d2dc14bf994957432245755861f0b5d0e8355213ffb8f81a38664bebd` |
| `INDEPENDENCE_MODEL.json` | `a04ff28822e1f3b851d5a7061f726de2e3711ebccd3d84e4237e5a54a1dc2b59` |
| `NON_COLLAPSE_RULES.json` | `7c64a1caff358b186f9d80f2e8dc1bfca704978f8bd987a9dc7dfb09c1c74786` |
| `PROPOSITION_SCHEMA.json` | `4ee9edf2e17b5728c5d53e9c17f5f7b5ce1792d296fe8da3ec4febd5d7118d6b` |
| `analysis_skeleton.py` | `c39476263a9643fdfe4a3a2e01a5882d83ad2eab2d3adc635722253112ce455a` |
| `condition_a.py` | `4fa0e54f4233a01587d14dd985e41455cb734dbf2f6eeee91d32808ae82ed664` |
| `condition_b.py` | `d217509d1a5c8074a803bf64c0e563da627132491cfc007c854eae8176c25f4b` |
| `condition_c_rats_plus.py` | `d544b106a87e4a2142a4b2b4cd1def94ca64cc42cfcd8022d4337dc4844522bc` |
| `generator.py` | `60363adc613b4718e0a7099415a0ed71d71a0637ad97b0a7326047e8e1fc1509` |
| `oracle.py` | `336d5a53b8248989ca3196f2ddf51f8801af5a8550738129afc893e6c9b8684d` |

## Remaining gates before confirmatory execution

1. An independent reviewer must inspect the frozen rule/oracle boundary and Condition A/B/C fairness under `INDEPENDENT_PREEXECUTION_REVIEW.md`.
2. Any accepted `BLOCKER` or `AMEND` finding must be implemented before result inspection and must trigger a new freeze record.
3. The confirmatory operator and execution environment must be recorded.
4. The record must state that no holdout result was inspected before any amendment.
5. Only after those gates may the >=1,000-case confirmatory corpus be generated and scored.

## Research-integrity boundary

This freeze establishes reproducibility of the pre-execution artifacts. It does **not** establish correctness, novelty, superiority, independent validation, or support for EA-C003. No confirmatory corpus or metric has been generated or inspected as part of this record.
