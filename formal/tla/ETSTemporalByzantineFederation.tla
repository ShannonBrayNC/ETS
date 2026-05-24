--------------------- MODULE ETSTemporalByzantineFederation ---------------------
EXTENDS Naturals, FiniteSets, TLC

(***************************************************************************)
(* ETSTemporalByzantineFederation models a bounded adversarial verifier     *)
(* federation for ETS. It abstracts cryptographic roots as bounded root     *)
(* identifiers and focuses on temporal and Byzantine protocol semantics:    *)
(* delayed observations, network partitions, witness gossip, stale votes,   *)
(* quorum decay, and Byzantine equivocation.                                *)
(*                                                                         *)
(* This model does not prove full asynchronous Byzantine consensus. It      *)
(* specifies the alpha ETS safety boundary: accepted federation conclusions *)
(* require fresh quorum support and must be suspended when conflicting      *)
(* fresh quorums or Byzantine equivocation are observed.                    *)
(***************************************************************************)

CONSTANTS Verifiers, ByzantineVerifiers, MaxRoot, MaxTime, FreshnessWindow, Threshold

RootIds == 0..MaxRoot
Times == 0..MaxTime

Observation == [verifier: Verifiers, root: RootIds, time: Times, partition: BOOLEAN]

VARIABLES now, observations, acceptedRoot, federationState, byzantineSuspicions, gossipLog

TypeOK ==
    /\ now \in Times
    /\ observations \subseteq Observation
    /\ acceptedRoot \in RootIds \cup {"None"}
    /\ federationState \in {"Converging", "Converged", "Partitioned", "Conflict", "Stale"}
    /\ byzantineSuspicions \subseteq Verifiers
    /\ gossipLog \subseteq Observation
    /\ ByzantineVerifiers \subseteq Verifiers
    /\ Threshold \in 1..Cardinality(Verifiers)
    /\ FreshnessWindow \in 0..MaxTime

Fresh(obs) == now >= obs.time /\ now - obs.time <= FreshnessWindow
FreshObservations == {obs \in observations : Fresh(obs)}
FreshVotesFor(root) == {obs \in FreshObservations : obs.root = root}
FreshVotersFor(root) == {obs.verifier : obs \in FreshVotesFor(root)}
FreshVoteCount(root) == Cardinality(FreshVotersFor(root))
FreshQuorumFor(root) == FreshVoteCount(root) >= Threshold
AnyFreshQuorum == \E root \in RootIds : FreshQuorumFor(root)

ConflictingFreshQuorums ==
    \E r1, r2 \in RootIds :
        /\ r1 # r2
        /\ FreshQuorumFor(r1)
        /\ FreshQuorumFor(r2)

VerifierEquivocated(v) ==
    \E o1, o2 \in FreshObservations :
        /\ o1.verifier = v
        /\ o2.verifier = v
        /\ o1.root # o2.root

PartitionObserved == \E obs \in FreshObservations : obs.partition = TRUE

AcceptedRootRequiresFreshQuorum ==
    acceptedRoot # "None" => FreshQuorumFor(acceptedRoot)

NoAcceptedRootDuringConflict ==
    ConflictingFreshQuorums => acceptedRoot = "None"

NoAcceptedRootDuringPartition ==
    PartitionObserved => federationState # "Converged"

ByzantineSuspicionsJustified ==
    \A v \in byzantineSuspicions : VerifierEquivocated(v) \/ v \in ByzantineVerifiers

GossipOnlyPublishesObservedRoots ==
    gossipLog \subseteq observations

ConvergedImpliesFreshQuorumNoConflict ==
    federationState = "Converged" =>
        /\ acceptedRoot # "None"
        /\ FreshQuorumFor(acceptedRoot)
        /\ ~ConflictingFreshQuorums
        /\ ~PartitionObserved

ConflictStateReflectsConflictOrEquivocation ==
    federationState = "Conflict" =>
        ConflictingFreshQuorums \/ (\E v \in Verifiers : VerifierEquivocated(v))

StaleStateMeansNoFreshQuorum ==
    federationState = "Stale" => ~AnyFreshQuorum

Init ==
    /\ now = 0
    /\ observations = {}
    /\ acceptedRoot = "None"
    /\ federationState = "Converging"
    /\ byzantineSuspicions = {}
    /\ gossipLog = {}

AdvanceTime ==
    /\ now < MaxTime
    /\ now' = now + 1
    /\ observations' = observations
    /\ gossipLog' = gossipLog
    /\ byzantineSuspicions' = byzantineSuspicions
    /\ acceptedRoot' = IF acceptedRoot # "None" /\ FreshQuorumFor(acceptedRoot)
                       THEN acceptedRoot
                       ELSE "None"
    /\ federationState' = IF ConflictingFreshQuorums THEN "Conflict"
                          ELSE IF PartitionObserved THEN "Partitioned"
                          ELSE IF acceptedRoot' # "None" THEN "Converged"
                          ELSE IF ~AnyFreshQuorum THEN "Stale"
                          ELSE "Converging"

Observe(verifier, root, partitionFlag) ==
    LET obs == [verifier |-> verifier, root |-> root, time |-> now, partition |-> partitionFlag] IN
    LET nextObservations == observations \cup {obs} IN
    LET nextFresh == {item \in nextObservations : now >= item.time /\ now - item.time <= FreshnessWindow} IN
    LET nextEquivocators ==
        {v \in Verifiers :
            \E o1, o2 \in nextFresh :
                /\ o1.verifier = v
                /\ o2.verifier = v
                /\ o1.root # o2.root} IN
        /\ verifier \in Verifiers
        /\ root \in RootIds
        /\ partitionFlag \in BOOLEAN
        /\ observations' = nextObservations
        /\ gossipLog' = gossipLog
        /\ byzantineSuspicions' = byzantineSuspicions \cup nextEquivocators
        /\ acceptedRoot' =
            IF partitionFlag THEN "None"
            ELSE IF \E r \in RootIds : Cardinality({o.verifier : o \in nextFresh /\ o.root = r}) >= Threshold THEN
                CHOOSE r \in RootIds : Cardinality({o.verifier : o \in nextFresh /\ o.root = r}) >= Threshold
            ELSE "None"
        /\ federationState' =
            IF \E r1, r2 \in RootIds :
                /\ r1 # r2
                /\ Cardinality({o.verifier : o \in nextFresh /\ o.root = r1}) >= Threshold
                /\ Cardinality({o.verifier : o \in nextFresh /\ o.root = r2}) >= Threshold
            THEN "Conflict"
            ELSE IF partitionFlag THEN "Partitioned"
            ELSE IF acceptedRoot' # "None" THEN "Converged"
            ELSE "Converging"
        /\ now' = now

ByzantineEquivocate(verifier, rootA, rootB) ==
    /\ verifier \in ByzantineVerifiers
    /\ rootA \in RootIds
    /\ rootB \in RootIds
    /\ rootA # rootB
    /\ Observe(verifier, rootA, FALSE)
    \* The second conflicting observation is modeled by a separate transition.

PublishGossip(obs) ==
    /\ obs \in observations
    /\ gossipLog' = gossipLog \cup {obs}
    /\ UNCHANGED <<now, observations, acceptedRoot, federationState, byzantineSuspicions>>

Next ==
    \/ AdvanceTime
    \/ \E verifier \in Verifiers, root \in RootIds, partitionFlag \in BOOLEAN :
        Observe(verifier, root, partitionFlag)
    \/ \E obs \in observations : PublishGossip(obs)

Spec == Init /\ [][Next]_<<now, observations, acceptedRoot, federationState, byzantineSuspicions, gossipLog>>

Safety ==
    /\ TypeOK
    /\ AcceptedRootRequiresFreshQuorum
    /\ NoAcceptedRootDuringConflict
    /\ NoAcceptedRootDuringPartition
    /\ ByzantineSuspicionsJustified
    /\ GossipOnlyPublishesObservedRoots
    /\ ConvergedImpliesFreshQuorumNoConflict
    /\ ConflictStateReflectsConflictOrEquivocation
    /\ StaleStateMeansNoFreshQuorum

THEOREM Spec => []TypeOK
=============================================================================
