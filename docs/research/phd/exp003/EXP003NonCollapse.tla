---- MODULE EXP003NonCollapse ----
EXTENDS Naturals

VARIABLES request,
          integrity,
          eventAuthority,
          currentAuthority,
          policyAtEvent,
          executionEvidence,
          resultEvidence,
          expectation,
          coverageGap,
          rootsIndependent,
          sharedRoot,
          semanticTrue,
          standing,
          executed,
          resultObserved,
          independent,
          eventAbsent

vars == <<request, integrity, eventAuthority, currentAuthority, policyAtEvent,
          executionEvidence, resultEvidence, expectation, coverageGap,
          rootsIndependent, sharedRoot, semanticTrue, standing, executed,
          resultObserved, independent, eventAbsent>>

Init ==
    /\ request \in BOOLEAN
    /\ integrity \in BOOLEAN
    /\ eventAuthority \in BOOLEAN
    /\ currentAuthority \in BOOLEAN
    /\ policyAtEvent \in BOOLEAN
    /\ executionEvidence \in BOOLEAN
    /\ resultEvidence \in BOOLEAN
    /\ expectation \in BOOLEAN
    /\ coverageGap \in BOOLEAN
    /\ rootsIndependent \in BOOLEAN
    /\ sharedRoot \in BOOLEAN
    /\ semanticTrue = FALSE
    /\ standing = (eventAuthority /\ policyAtEvent /\ request)
    /\ executed = executionEvidence
    /\ resultObserved = resultEvidence
    /\ independent = (rootsIndependent /\ ~sharedRoot)
    /\ eventAbsent = (expectation /\ coverageGap)

Next == UNCHANGED vars

Spec == Init /\ [][Next]_vars

NCIntegrityTruth == integrity => ~semanticTrue
NCRequestExecution == (~executionEvidence /\ request) => ~executed
NCExecutionResult == (~resultEvidence /\ executed) => ~resultObserved
NCCurrentAuthorityStanding ==
    (~eventAuthority /\ currentAuthority) => ~standing
NCSharedRootIndependence == sharedRoot => ~independent
NCOmissionExpectation == (~expectation \/ ~coverageGap) => ~eventAbsent

=============================================================================
