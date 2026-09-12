# EXP-002 Frozen Artifact Manifest

**Status:** PRE-EXECUTION FREEZE MANIFEST  
**Branch:** `research/phd-exp002-freeze`  
**Pinned commit before manifest creation:** `69d795f7db8cb2b7d822d10e0d2df97f6d3c0ec5`  
**Freeze date:** 2026-09-12

## Purpose

This manifest pins the semantic inputs used to prepare EXP-002. Git blob IDs are taken directly from GitHub's content API and identify the exact file contents committed at the pinned state.

Final SHA-256 values remain a mandatory execution gate because the current connector exposes Git object hashes and repository content but does not provide a direct byte-export hashing operation. No EXP-002 execution may begin until a local/CI freeze step computes SHA-256 for the final merged files and records those values in this manifest or a signed successor manifest.

## Frozen files

| Artifact | Size (bytes) | Git blob SHA |
|---|---:|---|
| `EA_CONDITION_SCHEMA.json` | 4212 | `8c06bb7489a63f77ea7a7a2a1336985b50c7964d` |
| `EQUIVALENCE_RUBRIC.md` | 8615 | `2e20f0f90b27aa943627be9670f8d1f9b6f4c808` |
| `NORMALIZED_CONCLUSION_SCHEMA.json` | 2808 | `7d59bb66c0d7921e8b6161825d2f11ee2ab3c806` |
| `RATS_BASELINE_ADVERSARIAL_REVIEW.md` | 4251 | `f5bad02ca146ec5f090ed6936e3bfc7e10635d08` |
| `RATS_CONDITION_SCHEMA.json` | 3574 | `da938912b644839a2c844e18b2d4d31e83cf487c` |
| `SCENARIO_CORPUS.json` | 9341 | `cee12b6327abe5084bec08e97a0d68525a691c8f` |
| `SEMANTIC_VOCABULARY.md` | 7197 | `191d574aa600a27872ba4035405ab2850b074c04` |

## Final SHA-256 freeze procedure

Before execution, from the final merged research commit:

```bash
cd docs/research/phd/exp002
sha256sum \
  EA_CONDITION_SCHEMA.json \
  EQUIVALENCE_RUBRIC.md \
  NORMALIZED_CONCLUSION_SCHEMA.json \
  RATS_BASELINE_ADVERSARIAL_REVIEW.md \
  RATS_CONDITION_SCHEMA.json \
  SCENARIO_CORPUS.json \
  SEMANTIC_VOCABULARY.md
```

Record:

- final repository commit SHA;
- each SHA-256 value;
- operator identity;
- timestamp;
- whether working tree was clean;
- tool/version used for hashing.

The resulting manifest must be committed before any scenario representation is scored.

## Mutation rule

Any change to a frozen artifact after final SHA-256 freeze invalidates the prior freeze. The change must be documented as a protocol amendment, all hashes regenerated, and reviewers informed before execution resumes.
