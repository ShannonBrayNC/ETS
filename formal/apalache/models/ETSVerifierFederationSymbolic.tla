---------------------- MODULE ETSVerifierFederationSymbolic ----------------------
EXTENDS Naturals, FiniteSets, TLC

(***************************************************************************)
(* Reduced symbolic-safe verifier federation model.                        *)
(*                                                                         *)
(* Preserves bounded quorum semantics and conflict visibility while         *)
(* minimizing unsupported symbolic complexity.                              *)
(***************************************************************************)

CONSTANTS Verifiers, Roots, Threshold

VARIABLES votes, accepted

TypeOK ==
    /\ votes \in [Verifiers -> Roots \cup {"NONE"}]
    /\ accepted \in BOOLEAN

VoteCount(root) ==
    Cardinality({v \in Verifiers : votes[v] = root})

HasQuorum ==
    \E root \in Roots : VoteCount(root) >= Threshold

ConflictingRoots ==
    \E r1, r2 \in Roots :
        /\ r1 # r2
        /\ VoteCount(r1) > 0
        /\ VoteCount(r2) > 0

Init ==
    /\ votes = [v \in Verifiers |-> "NONE"]
    /\ accepted = FALSE

CastVote(v, root) ==
    /\ v \in Verifiers
    /\ root \in Roots
    /\ votes' = [votes EXCEPT ![v] = root]
    /\ accepted' = accepted

AcceptRoot ==
    /\ HasQuorum
    /\ ~ConflictingRoots
    /\ accepted' = TRUE
    /\ votes' = votes

Next ==
    \/ \E v \in Verifiers, root \in Roots : CastVote(v, root)
    \/ AcceptRoot

AcceptedRequiresQuorum ==
    accepted => HasQuorum

NoAcceptedConflict ==
    accepted => ~ConflictingRoots

Spec == Init /\ [][Next]_<<votes, accepted>>

=============================================================================
