--------------------------- MODULE ETSProbabilisticTrust ---------------------------
EXTENDS Naturals, FiniteSets, TLC

(***************************************************************************)
(* ETSProbabilisticTrust models bounded confidence semantics for ETS        *)
(* verifier federation research. It intentionally avoids real probability   *)
(* distributions inside TLA+ and instead models discretized confidence      *)
(* levels through visible verifier support counts. This keeps the model     *)
(* executable by TLC while preserving the key safety questions: confidence  *)
(* acceptance, confidence suspension, selective visibility, eclipse          *)
(* suspicion, quorum churn, and adaptive adversary pressure.                *)
(*                                                                         *)
(* This model does not prove probabilistic security. It specifies bounded   *)
(* state-machine rules for how confidence may be accepted, degraded,        *)
(* suspended, or rejected under adversarial observation conditions.          *)
(***************************************************************************)

CONSTANTS Verifiers, Roots, AcceptThreshold, DegradedThreshold

VARIABLES visible, observations, acceptedRoot, confidence, adversaryMode, alerts

AlertTypes == {"None", "LowConfidence", "EclipseSuspected", "AdaptivePressure", "ConflictingTrustedRoots"}
AdversaryModes == {"Passive", "SelectiveVisibility", "Eclipse", "Adaptive"}
Observation == [verifier: Verifiers, root: Roots]

TypeOK ==
    /\ visible \subseteq Verifiers
    /\ observations \subseteq Observation
    /\ acceptedRoot \in Roots \cup {"None"}
    /\ confidence \in 0..Cardinality(Verifiers)
    /\ adversaryMode \in AdversaryModes
    /\ alerts \subseteq AlertTypes
    /\ AcceptThreshold \in 1..Cardinality(Verifiers)
    /\ DegradedThreshold \in 0..AcceptThreshold

VisibleVotesFor(root) == {obs.verifier : obs \in observations /\ obs.root = root /\ obs.verifier \in visible}
ConfidenceFor(root) == Cardinality(VisibleVotesFor(root))

RootAccepted(root) == ConfidenceFor(root) >= AcceptThreshold
ConflictingTrustedRoots ==
    \E r1, r2 \in Roots :
        /\ r1 # r2
        /\ RootAccepted(r1)
        /\ RootAccepted(r2)

EclipseSuspected == Cardinality(visible) < Cardinality(Verifiers)

AcceptedRootRequiresThreshold ==
    acceptedRoot # "None" => RootAccepted(acceptedRoot)

NoAcceptedRootOnConflictingTrustedRoots ==
    ConflictingTrustedRoots => acceptedRoot = "None"

LowConfidenceAlertSound ==
    "LowConfidence" \in alerts => confidence < AcceptThreshold

EclipseAlertSound ==
    "EclipseSuspected" \in alerts => EclipseSuspected

AdaptiveAlertSound ==
    "AdaptivePressure" \in alerts => adversaryMode = "Adaptive"

ConflictAlertSound ==
    "ConflictingTrustedRoots" \in alerts => ConflictingTrustedRoots

ConfidenceMatchesAcceptedRoot ==
    acceptedRoot # "None" => confidence = ConfidenceFor(acceptedRoot)

Init ==
    /\ visible = Verifiers
    /\ observations = {}
    /\ acceptedRoot = "None"
    /\ confidence = 0
    /\ adversaryMode = "Passive"
    /\ alerts = {}

NextAcceptedRoot(nextObservations, nextVisible) ==
    IF \E r1, r2 \in Roots :
        /\ r1 # r2
        /\ Cardinality({obs.verifier : obs \in nextObservations /\ obs.root = r1 /\ obs.verifier \in nextVisible}) >= AcceptThreshold
        /\ Cardinality({obs.verifier : obs \in nextObservations /\ obs.root = r2 /\ obs.verifier \in nextVisible}) >= AcceptThreshold
    THEN "None"
    ELSE IF \E r \in Roots : Cardinality({obs.verifier : obs \in nextObservations /\ obs.root = r /\ obs.verifier \in nextVisible}) >= AcceptThreshold
    THEN CHOOSE r \in Roots : Cardinality({obs.verifier : obs \in nextObservations /\ obs.root = r /\ obs.verifier \in nextVisible}) >= AcceptThreshold
    ELSE "None"

NextConfidence(nextAcceptedRoot, nextObservations, nextVisible) ==
    IF nextAcceptedRoot = "None" THEN 0
    ELSE Cardinality({obs.verifier : obs \in nextObservations /\ obs.root = nextAcceptedRoot /\ obs.verifier \in nextVisible})

NextConflict(nextObservations, nextVisible) ==
    \E r1, r2 \in Roots :
        /\ r1 # r2
        /\ Cardinality({obs.verifier : obs \in nextObservations /\ obs.root = r1 /\ obs.verifier \in nextVisible}) >= AcceptThreshold
        /\ Cardinality({obs.verifier : obs \in nextObservations /\ obs.root = r2 /\ obs.verifier \in nextVisible}) >= AcceptThreshold

Observe(verifier, root) ==
    LET nextObservations == observations \cup {[verifier |-> verifier, root |-> root]} IN
    LET nextAccepted == NextAcceptedRoot(nextObservations, visible) IN
    LET nextConfidence == NextConfidence(nextAccepted, nextObservations, visible) IN
        /\ verifier \in Verifiers
        /\ root \in Roots
        /\ observations' = nextObservations
        /\ UNCHANGED <<visible, adversaryMode>>
        /\ acceptedRoot' = nextAccepted
        /\ confidence' = nextConfidence
        /\ alerts' =
            (IF NextConflict(nextObservations, visible) THEN alerts \cup {"ConflictingTrustedRoots"} ELSE alerts) \cup
            (IF nextConfidence < AcceptThreshold THEN {"LowConfidence"} ELSE {})

HideVerifier(verifier) ==
    LET nextVisible == visible \ {verifier} IN
    LET nextAccepted == NextAcceptedRoot(observations, nextVisible) IN
    LET nextConfidence == NextConfidence(nextAccepted, observations, nextVisible) IN
        /\ verifier \in visible
        /\ visible' = nextVisible
        /\ adversaryMode' \in {"SelectiveVisibility", "Eclipse", "Adaptive"}
        /\ UNCHANGED observations
        /\ acceptedRoot' = nextAccepted
        /\ confidence' = nextConfidence
        /\ alerts' = alerts \cup {"EclipseSuspected", "LowConfidence"}

ShowVerifier(verifier) ==
    LET nextVisible == visible \cup {verifier} IN
    LET nextAccepted == NextAcceptedRoot(observations, nextVisible) IN
    LET nextConfidence == NextConfidence(nextAccepted, observations, nextVisible) IN
        /\ verifier \in Verifiers
        /\ visible' = nextVisible
        /\ UNCHANGED <<observations, adversaryMode>>
        /\ acceptedRoot' = nextAccepted
        /\ confidence' = nextConfidence
        /\ alerts' = alerts

AdaptivePressure ==
    /\ adversaryMode' = "Adaptive"
    /\ UNCHANGED <<visible, observations, acceptedRoot, confidence>>
    /\ alerts' = alerts \cup {"AdaptivePressure"}

Next ==
    \/ \E verifier \in Verifiers, root \in Roots : Observe(verifier, root)
    \/ \E verifier \in Verifiers : HideVerifier(verifier)
    \/ \E verifier \in Verifiers : ShowVerifier(verifier)
    \/ AdaptivePressure

Spec == Init /\ [][Next]_<<visible, observations, acceptedRoot, confidence, adversaryMode, alerts>>

Safety ==
    /\ TypeOK
    /\ AcceptedRootRequiresThreshold
    /\ NoAcceptedRootOnConflictingTrustedRoots
    /\ LowConfidenceAlertSound
    /\ EclipseAlertSound
    /\ AdaptiveAlertSound
    /\ ConflictAlertSound
    /\ ConfidenceMatchesAcceptedRoot

THEOREM Spec => []TypeOK
=============================================================================
