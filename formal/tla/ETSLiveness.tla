----------------------------- MODULE ETSLiveness -----------------------------
EXTENDS Naturals, TLC

CONSTANT MaxStep

VARIABLES step, partitioned, adversarialPressure, pendingReplay, witnessPropagated, staleState

Vars == <<step, partitioned, adversarialPressure, pendingReplay, witnessPropagated, staleState>>

TypeOK ==
    /\ step \in 0..MaxStep
    /\ partitioned \in BOOLEAN
    /\ adversarialPressure \in BOOLEAN
    /\ pendingReplay \in BOOLEAN
    /\ witnessPropagated \in BOOLEAN
    /\ staleState \in BOOLEAN

Init ==
    /\ step = 0
    /\ partitioned = TRUE
    /\ adversarialPressure = TRUE
    /\ pendingReplay = TRUE
    /\ witnessPropagated = FALSE
    /\ staleState = TRUE

Advance ==
    /\ step < MaxStep
    /\ step' = step + 1
    /\ UNCHANGED <<partitioned, adversarialPressure, pendingReplay, witnessPropagated, staleState>>

HealPartition ==
    /\ partitioned
    /\ partitioned' = FALSE
    /\ UNCHANGED <<step, adversarialPressure, pendingReplay, witnessPropagated, staleState>>

EndAdversarialPressure ==
    /\ adversarialPressure
    /\ adversarialPressure' = FALSE
    /\ UNCHANGED <<step, partitioned, pendingReplay, witnessPropagated, staleState>>

Replay ==
    /\ pendingReplay
    /\ ~partitioned
    /\ ~adversarialPressure
    /\ pendingReplay' = FALSE
    /\ UNCHANGED <<step, partitioned, adversarialPressure, witnessPropagated, staleState>>

PropagateWitness ==
    /\ ~pendingReplay
    /\ ~partitioned
    /\ witnessPropagated' = TRUE
    /\ UNCHANGED <<step, partitioned, adversarialPressure, pendingReplay, staleState>>

RecoverStaleState ==
    /\ witnessPropagated
    /\ staleState
    /\ staleState' = FALSE
    /\ UNCHANGED <<step, partitioned, adversarialPressure, pendingReplay, witnessPropagated>>

Next ==
    \/ Advance
    \/ HealPartition
    \/ EndAdversarialPressure
    \/ Replay
    \/ PropagateWitness
    \/ RecoverStaleState

Converged == ~pendingReplay /\ witnessPropagated /\ ~staleState

SafetyProgressBound == step <= MaxStep

PartitionHealingEventuality == partitioned ~> ~partitioned

ReplayEventuality == (~partitioned /\ ~adversarialPressure /\ pendingReplay) ~> ~pendingReplay

WitnessPropagationCompletion == (~pendingReplay /\ ~partitioned) ~> witnessPropagated

StaleStateRecovery == (witnessPropagated /\ staleState) ~> ~staleState

ConvergenceAfterAdversarialPressure ==
    (~partitioned /\ ~adversarialPressure) ~> Converged

Spec == Init /\ [][Next]_Vars

FairSpec ==
    Spec
    /\ WF_Vars(HealPartition)
    /\ WF_Vars(EndAdversarialPressure)
    /\ WF_Vars(Replay)
    /\ WF_Vars(PropagateWitness)
    /\ WF_Vars(RecoverStaleState)

THEOREM FairSpec => []TypeOK
=============================================================================
