# Wave 1 final R0 package — R0.16 operator trace, R0.17 HQP-2, and HQP-5 publication

**Tracking:** #906  
**Parent:** #814  
**Prerequisite implementation:** #904 / #905 (R0.15)

## Purpose

This is the final Wave 1 implementation gate after the physical R0.1–R0.15 corpus. It maps the remaining execution-plan gates directly: **R0.16** is one representative source-to-proof operator workflow; **R0.17** is clean off-DUT HQP-2 independent verification; and **HQP-5** is publication of the exact bounded qualification claim.

A merged implementation is not a qualification result. The final gate can pass only when actual retained physical phase evidence, an eligible HQP-2 result, and a published HQP-5 record are supplied.

## Final claim boundary

The final package preserves qualification_class=EDGE_COMPACT_R0, identity_profile=software_volume, hardware_attested=false, secure_boot_verified=false, and hardware_key_protection=false. R0 therefore establishes only the bounded physical evidence/recovery semantics of the exact tested DUT/build/profile. It does not establish hardware-attested identity.

## 1. Selected physical phase chain

The final package contains exactly R0.1 through R0.15 in order. Every selected phase binds its evaluation ID/schema and canonical digest, bench manifest and asset ID, predecessor evaluation, source/resulting build and configuration, approved upgrade/rollback/recovery transition binding when applicable, pre/post identity, checkpoint bounds where applicable, retained artifacts, independent observer receipts where required, independent verifier receipts where required, and the phase-only claim boundary.

The final assembler rejects broken predecessor, build/configuration, identity, or checkpoint continuity. R0.1 and R0.2 may legitimately refer to the same Phase 1 evaluation because that evaluation jointly establishes both gates.

## 2. R0.16 — source-to-proof operator trace

One representative event must be independently reviewable without hidden manual reconstruction. R0OperatorSourceToProofTrace binds source observation → source artifact → ingress receipt → event ID → Evidence Object → proof → exported bundle → independent verification result → external reviewer. The canonical trace commitment makes the selected chain immutable.

## 3. Failed and superseded runs

Failed, invalid, or superseded physical attempts remain retained. The final package keeps their run IDs, immutable package digests, historical state, reason, and successor ID when superseded. A later successful run does not erase failed evidence.

## 4. HQP-1 package binding

The final R0 package binds the exact profile ID/version/digest, run ID/digest, deterministic report ID/digest, run-package locator, qualification-report locator, artifact-manifest digest, Evidence Object IDs, and complete HQP input-package digest. These values are later compared directly to the independent HQP-2 result.

## 5. R0.17 — independent HQP-2 verification

Run the existing verifier away from the DUT:

    python3 -m ets.hqp_verify \
      --profile /retained/profile.json \
      --run /retained/hqp-run.json \
      --report /retained/hqp-report.json \
      --artifact-map /retained/artifact-map.json \
      --verifier-id '<immutable verifier identity>' \
      --verifier-build-digest '<sha256>' \
      --independent \
      --challenge-nonce '<retained challenge>'

Retain the machine-readable verifier result. The final publication evaluator requires outcome=valid, independent_execution_context=true, claimed-disposition eligibility, no missing required artifacts, no artifact digest mismatches, no invalid Evidence Object bindings, and exact profile/run/report ID and digest agreement with the final package. The DUT does not participate in the final verifier decision.

## 6. HQP-5 qualification-index claim

When and only when HQP-2 marks the claimed disposition eligible, generate the qualification-index claim. HQP qualified maps to qualification_state=qualified. HQP qualified_with_deviation maps to qualification_state=qualified_with_deviation. No other HQP claimed disposition can be promoted to a qualified index state.

The generated claim mirrors schemas/qualification/v1/qualification-index.schema.json and binds the exact profile/version, DUT/revision/asset/firmware, final build/artifact/configuration, HQP run/report/artifact manifest, Evidence Object IDs, independent verifier identity/result/digest, canonical R0 limitations, validity, and supersession fields.

## 7. Publication receipt

The final gate also requires evidence that the claim was actually inserted into the governed qualification registry. Wave1R0PublicationReceipt binds the claim ID, qualification state, registry locator, digest of the published registry artifact, publication time, final R0 package root, HQP-2 verification digest, and independent publication observation. Without that receipt, the package may be eligible for publication but Wave 1 is not closed as a published physical qualification.

## 8. Final evaluator

    python3 -m ets.physical_edge_final evaluate-publication \
      --package /retained/wave1-r0-final-package.json \
      --hqp2-verification /retained/hqp2-verification.json \
      --index-claim /retained/qualification-index-claim.json \
      --publication-receipt /retained/publication-receipt.json \
      --output /retained/wave1-r0-final-disposition.json \
      --summary /retained/wave1-r0-final-summary.txt

A successful result requires wave1_r0_publication_gate_passed=true and qualification_state=qualified, or qualification_state=qualified_with_deviation when profile/governance permits and the retained HQP result supports it.

## 9. Package root

The complete final manifest receives a canonical package-root SHA-256 over all fields except the root itself. Any selected phase, historical-run reference, operator trace, HQP binding, DUT identity, build, limitation, or trust-posture change therefore changes the package root.

## 10. Requalification

Publication does not create indefinite equivalence. The HQP-5 governance triggers remain authoritative, including material changes to DUT model/revision, storage/network hardware or claim-critical firmware, build/artifact/configuration, identity/signing-key handling, evidence/proof schema affecting verification, qualification profile/corpus, verifier contract, or claim-critical environment. A superseding claim must preserve the older package and index history.

## 11. Implementation versus execution

CI may prove that this final assembler/evaluator correctly rejects malformed synthetic packages. CI does not prove any physical R0 phase occurred, the actual DUT passed R0.1–R0.15, the R0.16 trace exists for the real device, HQP-2 verified a real physical package, or HQP-5 contains a real R0 claim. Those states require retained physical evidence and the final publication receipt.

## Follow-on

After a real #906 gate passes: close Wave 1 #814 with the exact published R0 claim reference; begin Edge Enterprise R1 TPM/Secure Boot/hardware-key qualification; and separately run Edge Compact ARM constrained qualification/endurance.
