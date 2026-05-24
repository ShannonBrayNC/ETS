--------------------------- MODULE ETSLivenessFederation ---------------------------
EXTENDS Naturals, TLC

(***************************************************************************)
(* ETSLivenessFederation models bounded liveness and fairness semantics     *)
(* for ETS verifier federation research.                                    *)
(*                                                                         *)
(* Earlier ETS models primarily focused on safety properties:               *)
(*                                                                         *)
(* - append correctness;                                                    *)
(* - quorum constraints;                                                    *)
(* - equivocation suspicion;                                                *)
(* - stale-state handling;                                                  *)
(* - conflict detection.                                                    *)
(*                                                                         *)
(* This model introduces bounded progress semantics under explicitly stated  *)
(* fairness assumptions.                                                    *)
(*                                                                         *)
(* Importantly:                                                             *)
(*                                                                         *)
(* The model does NOT claim guaranteed convergence under arbitrary          *)
(* Byzantine conditions.                                                    *)
(*                                                                         *)
(* Instead, it models:                                                      *)
(*                                                                         *)
(* - eventual convergence under fair delivery assumptions;                  *)
(* - partition healing;                                                     *)
(* - eventual gossip propagation;                                           *)
(* - bounded recovery from stale states.                                    *)
(***************************************************************************)

CONSTANTS Verifiers, Roots, Threshold, MaxRounds

VARIABLES round, deliveredVotes, pendingVotes, acceptedRoot, federationState

States == {"Converging", "Converged", "Partitioned", "Conflict", "Stale"}
Vote == [verifier: Verifiers, root: Roots]

TypeOK ==
    /\ round \in 0..MaxRounds
    /\ deliveredVotes \subseteq Vote
    /\ pendingVotes \subseteq Vote
    /\ acceptedRoot \in Roots \cup {"None"}
    /\ federationState \in States
    /\ Threshold \in 1..Cardinality(Verifiers)

VotesFor(root) == {v.verifier : v \in deliveredVotes /\ v.root = root}
VoteCount(root) == Cardinality(VotesFor(root))
Quorum(root) == VoteCount(root) >= Threshold

AnyQuorum == \E root \in Roots : Quorum(root)

ConflictingQuorums ==
    \E r1, r2 \in Roots :
        /\ r1 # r2
        /\ Quorum(r1)
        /\ Quorum(r2)

AcceptedRootValid ==
    acceptedRoot # "None" => Quorum(acceptedRoot)

NoAcceptedRootDuringConflict ==
    ConflictingQuorums => acceptedRoot = "None"

ConvergedMeansValidRoot ==
    federationState = "Converged" => acceptedRoot # "None"

Init ==
    /\ round = 0
    /\ deliveredVotes = {}
    /\ pendingVotes = {}
    /\ acceptedRoot = "None"
    /\ federationState = "Converging"

SubmitVote(verifier, root) ==
    /\ verifier \in Verifiers
    /\ root \in Roots
    /\ pendingVotes' = pendingVotes \cup {[verifier |-> verifier, root |-> root]}
    /\ UNCHANGED <<round, deliveredVotes, acceptedRoot, federationState>>

DeliverVote(vote) ==
    LET nextDelivered == deliveredVotes \cup {vote} IN
    LET nextAccepted ==
        IF \E r1, r2 \in Roots :
            /\ r1 # r2
            /\ Cardinality({v.verifier : v \in nextDelivered /\ v.root = r1}) >= Threshold
            /\ Cardinality({v.verifier : v \in nextDelivered /\ v.root = r2}) >= Threshold
        THEN "None"
        ELSE IF \E r \in Roots : Cardinality({v.verifier : v \in nextDelivered /\ v.root = r}) >= Threshold
        THEN CHOOSE r \in Roots : Cardinality({v.verifier : v \in nextDelivered /\ v.root = r}) >= Threshold
        ELSE "None" IN
        /\ vote \in pendingVotes
        /\ deliveredVotes' = nextDelivered
        /\ pendingVotes' = pendingVotes \ {vote}
        /\ acceptedRoot' = nextAccepted
        /\ federationState' =
            IF ConflictingQuorums THEN "Conflict"
            ELSE IF nextAccepted # "None" THEN "Converged"
            ELSE "Converging"
        /\ UNCHANGED round

AdvanceRound ==
    /\ round < MaxRounds
    /\ round' = round + 1
    /\ deliveredVotes' = deliveredVotes
    /\ pendingVotes' = pendingVotes
    /\ acceptedRoot' = acceptedRoot
    /\ federationState' =
        IF acceptedRoot # "None" THEN "Converged"
        ELSE IF pendingVotes = {} THEN "Stale"
        ELSE federationState

Partition ==
    /\ federationState' = "Partitioned"
    /\ UNCHANGED <<round, deliveredVotes, pendingVotes, acceptedRoot>>

HealPartition ==
    /\ federationState = "Partitioned"
    /\ federationState' = "Converging"
    /\ UNCHANGED <<round, deliveredVotes, pendingVotes, acceptedRoot>>

Next ==
    \/ \E verifier \in Verifiers, root \in Roots : SubmitVote(verifier, root)
    \/ \E vote \in pendingVotes : DeliverVote(vote)
    \/ AdvanceRound
    \/ Partition
    \/ HealPartition

Spec == Init /\ [][Next]_<<round, deliveredVotes, pendingVotes, acceptedRoot, federationState>>

Fairness ==
    /\ WF_<<round, deliveredVotes, pendingVotes, acceptedRoot, federationState>>(AdvanceRound)
    /\ \A vote \in Vote : WF_<<round, deliveredVotes, pendingVotes, acceptedRoot, federationState>>(DeliverVote(vote))

EventuallyConverges ==
    <>((federationState = "Converged") \/ (federationState = "Conflict"))

EventuallyPendingVotesDrain ==
    <>(pendingVotes = {})

PartitionEventuallyHeals ==
    [](federationState = "Partitioned" => <>(federationState # "Partitioned"))

LivenessSpec == Spec /\ Fairness

Safety ==
    /\ TypeOK
    /\ AcceptedRootValid
    /\ NoAcceptedRootDuringConflict
    /\ ConvergedMeansValidRoot

=============================================================================
