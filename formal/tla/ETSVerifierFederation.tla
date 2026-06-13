------------------------- MODULE ETSVerifierFederation -------------------------
EXTENDS Naturals, FiniteSets, TLC

(***************************************************************************)
(* ETSVerifierFederation models quorum and convergence semantics for an     *)
(* ETS verifier federation. It abstracts cryptographic roots as bounded     *)
(* identifiers and focuses on protocol-state behavior: votes, quorum,       *)
(* conflicting observations, equivocation suspicion, and convergence.       *)
(*                                                                         *)
(* This model does not prove cryptographic soundness. It checks that the    *)
(* federation never accepts two different roots for the same view and that  *)
(* quorum acceptance requires enough matching verifier observations.        *)
(***************************************************************************)

CONSTANTS Verifiers, MaxRoot, Threshold

RootIds == 0..MaxRoot
NoRoot == MaxRoot + 1
RootView == [root: RootIds]
Vote == [verifier: Verifiers, root: RootIds]

VARIABLES votes, acceptedRoot, conflictDetected, equivocationSuspicions

TypeOK ==
    /\ votes \subseteq Vote
    /\ acceptedRoot \in RootIds \cup {NoRoot}
    /\ conflictDetected \in BOOLEAN
    /\ equivocationSuspicions \subseteq Verifiers
    /\ Threshold \in 1..Cardinality(Verifiers)

VotesFor(root) == {v \in votes : v.root = root}
VerifierSetFor(root) ==
    {verifier \in Verifiers :
        \E submittedVote \in VotesFor(root) :
            submittedVote.verifier = verifier}
VoteCount(root) == Cardinality(VerifierSetFor(root))

QuorumFor(root) == VoteCount(root) >= Threshold
AnyQuorum == \E root \in RootIds : QuorumFor(root)

ConflictingQuorums ==
    \E r1, r2 \in RootIds :
        /\ r1 # r2
        /\ QuorumFor(r1)
        /\ QuorumFor(r2)

VerifierEquivocated(verifier) ==
    \E v1, v2 \in votes :
        /\ v1.verifier = verifier
        /\ v2.verifier = verifier
        /\ v1.root # v2.root

AcceptedRootHasQuorum ==
    acceptedRoot # NoRoot => QuorumFor(acceptedRoot)

NoConflictingAcceptedRoots ==
    ~(\E r1, r2 \in RootIds :
        /\ r1 # r2
        /\ acceptedRoot = r1
        /\ acceptedRoot = r2)

ConflictFlagReflectsConflictingQuorums ==
    conflictDetected => ConflictingQuorums

EquivocationSuspicionsAreJustified ==
    \A verifier \in equivocationSuspicions : VerifierEquivocated(verifier)

Init ==
    /\ votes = {}
    /\ acceptedRoot = NoRoot
    /\ conflictDetected = FALSE
    /\ equivocationSuspicions = {}

CastVote(verifier, root) ==
    LET newVote == [verifier |-> verifier, root |-> root] IN
    LET nextVotes == votes \cup {newVote} IN
        /\ verifier \in Verifiers
        /\ root \in RootIds
        /\ votes' = nextVotes
        /\ equivocationSuspicions' =
            equivocationSuspicions \cup
            {v \in Verifiers :
                \E v1, v2 \in nextVotes :
                    /\ v1.verifier = v
                    /\ v2.verifier = v
                    /\ v1.root # v2.root}
        /\ conflictDetected' =
            (conflictDetected \/
            (\E r1, r2 \in RootIds :
                /\ r1 # r2
                /\ Cardinality({v \in Verifiers :
                    \E submittedVote \in nextVotes :
                        /\ submittedVote.verifier = v
                        /\ submittedVote.root = r1}) >= Threshold
                /\ Cardinality({v \in Verifiers :
                    \E submittedVote \in nextVotes :
                        /\ submittedVote.verifier = v
                        /\ submittedVote.root = r2}) >= Threshold))
        /\ acceptedRoot' =
            IF acceptedRoot # NoRoot THEN acceptedRoot
            ELSE IF ~conflictDetected' THEN
                CHOOSE r \in RootIds \cup {NoRoot} :
                    \/ r = NoRoot /\ ~(\E candidate \in RootIds :
                        Cardinality({v \in Verifiers :
                            \E submittedVote \in nextVotes :
                                /\ submittedVote.verifier = v
                                /\ submittedVote.root = candidate}) >= Threshold)
                    \/ r \in RootIds /\ Cardinality({v \in Verifiers :
                        \E submittedVote \in nextVotes :
                            /\ submittedVote.verifier = v
                            /\ submittedVote.root = r}) >= Threshold
            ELSE NoRoot

Next ==
    \E verifier \in Verifiers, root \in RootIds : CastVote(verifier, root)

Spec == Init /\ [][Next]_<<votes, acceptedRoot, conflictDetected, equivocationSuspicions>>

Safety ==
    /\ TypeOK
    /\ AcceptedRootHasQuorum
    /\ NoConflictingAcceptedRoots
    /\ ConflictFlagReflectsConflictingQuorums
    /\ EquivocationSuspicionsAreJustified

THEOREM Spec => []TypeOK
=============================================================================
