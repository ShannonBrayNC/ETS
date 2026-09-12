# EXP-002 — External RATS Review Request

**Status:** ready for outreach, not yet sent  
**Primary proposed recipient:** Ned Smith  
**Alternate:** Henk Birkholz

## Proposed subject

Independent technical review request — RATS equivalence falsification study

## Proposed message

Ned,

I am developing a doctoral research programme around independently verifiable evidence for consequential machine actions. One of the candidate contributions is being tested against the IETF RATS architecture rather than assumed to be novel.

I have preregistered a falsification study, EXP-002, whose purpose is to determine whether a sufficiently rich RFC 9334/RATS profile can reproduce the semantic distinctions I have been calling Evidence Architecture: integrity, identity, provenance, historical authority/standing, requested action, execution, result observation, uncertainty/nonclaims, and related boundaries.

The internal red-team pass has already produced an adverse result for my broader claims: using rich Claims, Attestation Results, application-specific policy, multiple Attesters/Verifiers, historical policy state and source/derivation information, all 20 frozen scenarios currently appear representable within a strong RATS profile. I am preserving that result rather than tuning the baseline to make ETS win.

Before EXP-002 can be used as doctoral evidence, I want an independent RATS expert to try to defeat the remaining differentiation. Given your role in RFC 9334 and current RATS work, would you be willing to review the frozen comparison package, or point me to someone you consider better suited?

The requested review is deliberately adversarial. I would ask you to identify stronger ordinary-RATS encodings, challenge any classification that overstates a gap, and flag any rule I have incorrectly treated as outside ordinary RATS profiling. A conclusion that the ETS semantics reduce to a RATS application profile is a valid and useful research result.

The package is public and includes the preregistration, 20-scenario corpus, strongest-RATS profile, equivalence rubric, internal red-team findings, and reviewer brief. I can send the exact repository links in a compact review index.

There is no request to endorse ETS, the product, or any originality claim. I am specifically looking for a technically credible attempt to falsify those claims before the work proceeds further.

Regards,
Shannon Bray

## Reviewer deliverable requested

A concise review is sufficient if it records:

- reviewer identity/date and independence disclosure;
- scenario-by-scenario corrections where the internal baseline is weak;
- whether each disputed distinction is ordinary RATS architecture, ordinary application profile, requires an extra normative rule, or remains unresolved;
- references to relevant RFCs, drafts, implementations or established practice;
- confirmation that the comparison is not knowingly using a straw-man RATS profile.

No endorsement or agreement with Evidence Architecture is requested.
