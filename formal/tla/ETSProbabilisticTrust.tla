--------------------------- MODULE ETSProbabilisticTrust ---------------------------
EXTENDS Naturals, FiniteSets, TLC

(***************************************************************************)
(* ETSProbabilisticTrust models bounded confidence semantics for ETS        *)
(* verifier federation research. It intentionally avoids real probability   *)
(* distributions inside TLA+ and instead models discretized confidence      *)
(* levels. This allows TLC to check safety properties around trust decay,    *)
(* weighted verifier observations, selective visibility, eclipse suspicion, *)
(* quorum churn, and adaptive adversary pressure.                           *)
(*                                                                         *)
(* This model does not prove probabilistic security. It specifies bounded   *)
(* state-machine rules for how confidence may be accepted, degraded,        *)
(* suspended, or rejected under adversarial observation conditions.          *)
(***************************************************************************)

CONSTANTS Verifiers, Roots, MaxTrust, AcceptThreshold, DegradedThreshold

VARIABLES trust, visible, observations, acceptedRoot, confidence, adversaryMode, alerts

AlertTypes == {"None", "LowConfidence", "EclipseSuspected", "AdaptivePressure", "ConflictingTrustedRoots"}
AdversaryModes == {"Passive", "SelectiveVisibility", "Eclipse", "Adaptive"}

Observation == [verifier: Verifiers, root: Roots]

TypeOK ==
    /\ trust \in [Verifiers -> 0..MaxTrust]
    /\ visible \subseteq Verifiers
    /\ observations \subseteq Observation
    /\ acceptedRoot \in Roots \cup {"None"}
    /\ confidence \in 0..(Cardinality(Verifiers) * MaxTrust)
    /\ adversaryMode \in AdversaryModes
    /\ alerts \subseteq AlertTypes
    /\ AcceptThreshold \in 1..(Cardinality(Verifiers) * MaxTrust)
    /\ DegradedThreshold \in 0..AcceptThreshold

VisibleObservation(obs) == obs.verifier \in visible
TrustedWeightFor(root) ==
    Sum({trust[obs.verifier] : obs \in observations /\ obs.root = root /\ VisibleObservation(obs)})

AnyAcceptedRoot == \E root \in Roots : TrustedWeightFor(root) >= AcceptThreshold

ConflictingTrustedRoots ==
    \E r1, r2 \in Roots :
        /\ r1 # r2
        /\ TrustedWeightFor(r1) >= AcceptThreshold
        /\ TrustedWeightFor(r2) >= AcceptThreshold

EclipseSuspected == Cardinality(visible) < Cardinality(Verifiers)

AcceptedRootRequiresThreshold ==
    acceptedRoot # "None" => TrustedWeightFor(acceptedRoot) >= AcceptThreshold

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
    acceptedRoot # "None" => confidence = TrustedWeightFor(acceptedRoot)

InitTrust == [v \in Verifiers |-> MaxTrust]

Init ==
    /\ trust = InitTrust
    /\ visible = Verifiers
    /\ observations = {}
    /\ acceptedRoot = "None"
    /\ confidence = 0
    /\ adversaryMode = "Passive"
    /\ alerts = {}

Observe(verifier, root) ==
    LET obs == [verifier |-> verifier, root |-> root] IN
    LET nextObservations == observations \cup {obs} IN
    LET nextConflict ==
        \E r1, r2 \in Roots :
            /\ r1 # r2
            /\ Sum({trust[o.verifier] : o \in nextObservations /\ o.root = r1 /\ o.verifier \in visible}) >= AcceptThreshold
            /\ Sum({trust[o.verifier] : o \in nextObservations /\ o.root = r2 /\ o.verifier \in visible}) >= AcceptThreshold IN
        /\ verifier \in Verifiers
        /\ root \in Roots
        /\ observations' = nextObservations
        /\ UNCHANGED <<trust, visible, adversaryMode>>
        /\ acceptedRoot' =
            IF nextConflict THEN "None"
            ELSE IF \E r \in Roots : Sum({trust[o.verifier] : o \in nextObservations /\ o.root = r /\ o.verifier \in visible}) >= AcceptThreshold THEN
                CHOOSE r \in Roots : Sum({trust[o.verifier] : o \in nextObservations /\ o.root = r /\ o.verifier \in visible}) >= AcceptThreshold
            ELSE "None"
        /\ confidence' = IF acceptedRoot' = "None" THEN 0
                         ELSE Sum({trust[o.verifier] : o \in nextObservations /\ o.root = acceptedRoot' /\ o.verifier \in visible})
        /\ alerts' =
            (IF nextConflict THEN alerts \cup {"ConflictingTrustedRoots"} ELSE alerts) \cup
            (IF confidence' < AcceptThreshold THEN {"LowConfidence"} ELSE {})

DecayTrust(verifier) ==
    /\ verifier \in Verifiers
    /\ trust[verifier] > 0
    /\ trust' = [trust EXCEPT ![verifier] = @ - 1]
    /\ UNCHANGED <<visible, observations, adversaryMode>>
    /\ acceptedRoot' = IF acceptedRoot # "None" /\ TrustedWeightFor(acceptedRoot) >= AcceptThreshold THEN acceptedRoot ELSE "None"
    /\ confidence' = IF acceptedRoot' = "None" THEN 0 ELSE TrustedWeightFor(acceptedRoot')
    /\ alerts' = IF confidence' < AcceptThreshold THEN alerts \cup {"LowConfidence"} ELSE alerts

RestoreTrust(verifier) ==
    /\ verifier \in Verifiers
    /\ trust[verifier] < MaxTrust
    /\ trust' = [trust EXCEPT ![verifier] = @ + 1]
    /\ UNCHANGED <<visible, observations, adversaryMode>>
    /\ acceptedRoot' = acceptedRoot
    /\ confidence' = confidence
    /\ alerts' = alerts

HideVerifier(verifier) ==
    /\ verifier \in visible
    /\ visible' = visible \ {verifier}
    /\ adversaryMode' \in {"SelectiveVisibility", "Eclipse", "Adaptive"}
    /\ UNCHANGED <<trust, observations>>
    /\ acceptedRoot' = "None"
    /\ confidence' = 0
    /\ alerts' = alerts \cup {"EclipseSuspected", "LowConfidence"}

ShowVerifier(verifier) ==
    /\ verifier \in Verifiers
    /\ visible' = visible \cup {verifier}
    /\ UNCHANGED <<trust, observations, adversaryMode>>
    /\ acceptedRoot' = acceptedRoot
    /\ confidence' = confidence
    /\ alerts' = alerts

AdaptivePressure ==
    /\ adversaryMode' = "Adaptive"
    /\ UNCHANGED <<trust, visible, observations, acceptedRoot, confidence>>
    /\ alerts' = alerts \cup {"AdaptivePressure"}

Next ==
    \/ \E verifier \in Verifiers, root \in Roots : Observe(verifier, root)
    \/ \E verifier \in Verifiers : DecayTrust(verifier)
    \/ \E verifier \in Verifiers : RestoreTrust(verifier)
    \/ \E verifier \in Verifiers : HideVerifier(verifier)
    \/ \E verifier \in Verifiers : ShowVerifier(verifier)
    \/ AdaptivePressure

Spec == Init /\ [][Next]_<<trust, visible, observations, acceptedRoot, confidence, adversaryMode, alerts>>

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
