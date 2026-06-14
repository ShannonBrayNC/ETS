----------------------------- MODULE ETSLog -----------------------------
EXTENDS Naturals, Sequences, FiniteSets, TLC

(***************************************************************************)
(* ETSLog models the alpha ETS transparency-log state machine at the level  *)
(* needed for protocol reasoning. It intentionally abstracts cryptographic  *)
(* hashes into bounded root identifiers. This model does not prove SHA-256  *)
(* security. It checks state-machine obligations around append-only growth, *)
(* verifier root disagreement, and omission suspicion relative to an        *)
(* externally supplied expected-event set.                                  *)
(*                                                                         *)
(* Non-goals: this model does not prove real-world truth, legal             *)
(* sufficiency, election correctness, SHA-256 security, hosted identity     *)
(* correctness, cloud durability, or completeness without an external       *)
(* expected-event policy and observation process.                           *)
(***************************************************************************)

CONSTANTS MaxEntries, MaxRoot, Verifiers, ExpectedEvents

VARIABLES log, observedRoots, forkDetected, missingSuspicions

EventIds == 1..MaxEntries
RootIds == 0..MaxRoot
TreeSizes == 0..MaxEntries

Observation == [verifier: Verifiers, treeSize: TreeSizes, root: RootIds]

SeqRange(seq) == {seq[i] : i \in DOMAIN seq}

TypeOK ==
    /\ log \in Seq(EventIds)
    /\ observedRoots \subseteq Observation
    /\ forkDetected \in BOOLEAN
    /\ missingSuspicions \subseteq ExpectedEvents

NoDuplicateLogEntries ==
    \A i, j \in DOMAIN log : i # j => log[i] # log[j]

LogIndexDomainContiguous ==
    DOMAIN log = 1..Len(log)

ExpectedEventsWellFormed ==
    ExpectedEvents \subseteq EventIds

ObservedTreeSizesBounded ==
    \A obs \in observedRoots : obs.treeSize <= Len(log) \/ forkDetected

MissingSuspicionsRequireExpectation ==
    missingSuspicions \subseteq ExpectedEvents

MissingSuspicionsAreAbsentAtDetectionBoundary ==
    \A event \in missingSuspicions : event \notin SeqRange(log)

RootConflictExists ==
    \E o1, o2 \in observedRoots :
        /\ o1.treeSize = o2.treeSize
        /\ o1.root # o2.root

ForkFlagRequiresConflict ==
    forkDetected => RootConflictExists

Init ==
    /\ log = << >>
    /\ observedRoots = {}
    /\ forkDetected = FALSE
    /\ missingSuspicions = {}

AppendEntry(event) ==
    /\ Len(log) < MaxEntries
    /\ event \in EventIds
    /\ event \notin SeqRange(log)
    /\ log' = Append(log, event)
    /\ observedRoots' = observedRoots
    /\ forkDetected' = forkDetected
    /\ missingSuspicions' = missingSuspicions \ {event}

ObserveRoot(verifier, treeSize, root) ==
    LET newObservation == [verifier |-> verifier, treeSize |-> treeSize, root |-> root] IN
    LET nextObserved == observedRoots \cup {newObservation} IN
        /\ verifier \in Verifiers
        /\ treeSize \in TreeSizes
        /\ treeSize <= Len(log)
        /\ root \in RootIds
        /\ log' = log
        /\ observedRoots' = nextObserved
        /\ forkDetected' =
            (forkDetected \/
            (\E prior \in observedRoots :
                /\ prior.treeSize = treeSize
                /\ prior.root # root))
        /\ missingSuspicions' = missingSuspicions

DetectMissing(event) ==
    /\ event \in ExpectedEvents
    /\ event \notin SeqRange(log)
    /\ log' = log
    /\ observedRoots' = observedRoots
    /\ forkDetected' = forkDetected
    /\ missingSuspicions' = missingSuspicions \cup {event}

Next ==
    \/ \E event \in EventIds : AppendEntry(event)
    \/ \E verifier \in Verifiers, treeSize \in TreeSizes, root \in RootIds :
        ObserveRoot(verifier, treeSize, root)
    \/ \E event \in ExpectedEvents : DetectMissing(event)

Spec == Init /\ [][Next]_<<log, observedRoots, forkDetected, missingSuspicions>>

Safety ==
    /\ TypeOK
    /\ NoDuplicateLogEntries
    /\ LogIndexDomainContiguous
    /\ ExpectedEventsWellFormed
    /\ ObservedTreeSizesBounded
    /\ MissingSuspicionsRequireExpectation
    /\ MissingSuspicionsAreAbsentAtDetectionBoundary
    /\ ForkFlagRequiresConflict

THEOREM Spec => []TypeOK
=============================================================================
