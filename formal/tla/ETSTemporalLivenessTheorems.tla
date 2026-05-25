------------------------- MODULE ETSTemporalLivenessTheorems -------------------------
EXTENDS Naturals, TLC

(***************************************************************************)
(* ETSTemporalLivenessTheorems defines bounded theorem-style temporal       *)
(* liveness properties for ETS.                                             *)
(*                                                                         *)
(* Research boundary:                                                       *)
(* This model does not prove universal liveness under arbitrary Byzantine   *)
(* scheduling. It formalizes bounded temporal progress under explicit       *)
(* assumptions: finite delay, eventual partition healing, and enabled       *)
(* resolution actions.                                                      *)
(***************************************************************************)

CONSTANT MaxTime

VARIABLES time, partitioned, pending, resolved, conflicted

TypeOK ==
    /\ time \in 0..MaxTime
    /\ partitioned \in BOOLEAN
    /\ pending \in BOOLEAN
    /\ resolved \in BOOLEAN
    /\ conflicted \in BOOLEAN

Init ==
    /\ time = 0
    /\ partitioned = TRUE
    /\ pending = TRUE
    /\ resolved = FALSE
    /\ conflicted = FALSE

AdvanceTime ==
    /\ time < MaxTime
    /\ time' = time + 1
    /\ UNCHANGED <<partitioned, pending, resolved, conflicted>>

HealPartition ==
    /\ partitioned
    /\ partitioned' = FALSE
    /\ UNCHANGED <<time, pending, resolved, conflicted>>

ResolvePending ==
    /\ ~partitioned
    /\ pending
    /\ pending' = FALSE
    /\ resolved' = TRUE
    /\ conflicted' = FALSE
    /\ UNCHANGED <<time, partitioned>>

DetectConflict ==
    /\ ~partitioned
    /\ pending
    /\ pending' = FALSE
    /\ resolved' = FALSE
    /\ conflicted' = TRUE
    /\ UNCHANGED <<time, partitioned>>

TimeoutResolution ==
    /\ time = MaxTime
    /\ pending
    /\ pending' = FALSE
    /\ resolved' = resolved
    /\ conflicted' = TRUE
    /\ partitioned' = partitioned
    /\ time' = time

TerminalStutter ==
    /\ ~pending
    /\ UNCHANGED <<time, partitioned, pending, resolved, conflicted>>

Next ==
    \/ AdvanceTime
    \/ HealPartition
    \/ ResolvePending
    \/ DetectConflict
    \/ TimeoutResolution
    \/ TerminalStutter

Spec == Init /\ [][Next]_<<time, partitioned, pending, resolved, conflicted>>

FairSpec ==
    Spec
    /\ WF_<<time, partitioned, pending, resolved, conflicted>>(HealPartition)
    /\ WF_<<time, partitioned, pending, resolved, conflicted>>(ResolvePending)
    /\ WF_<<time, partitioned, pending, resolved, conflicted>>(DetectConflict)
    /\ WF_<<time, partitioned, pending, resolved, conflicted>>(TimeoutResolution)

TerminalMeansNoPending ==
    (resolved \/ conflicted) => ~pending

NoResolvedConflictOverlap ==
    ~(resolved /\ conflicted)

PendingEventuallyEnds ==
    <>(~pending)

PartitionEventuallyHealsOrTerminal ==
    <>(~partitioned \/ ~pending)

ResolutionEventuallyClassified ==
    <>(resolved \/ conflicted)

=============================================================================
