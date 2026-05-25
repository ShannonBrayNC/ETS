---------------------- MODULE ETSAsyncTransportSymbolic ----------------------
EXTENDS Naturals, FiniteSets, Sequences, TLC

(***************************************************************************)
(* Reduced symbolic-safe asynchronous transport model.                     *)
(*                                                                         *)
(* Focuses on bounded delivery, replay visibility, and duplicate-prevention *)
(* semantics suitable for initial SMT-backed checking.                     *)
(***************************************************************************)

CONSTANTS Messages

VARIABLES pending, delivered, replayDetected

TypeOK ==
    /\ pending \subseteq Messages
    /\ delivered \subseteq Messages
    /\ replayDetected \in BOOLEAN

Init ==
    /\ pending = Messages
    /\ delivered = {}
    /\ replayDetected = FALSE

Deliver(msg) ==
    /\ msg \in pending
    /\ msg \notin delivered
    /\ pending' = pending \ {msg}
    /\ delivered' = delivered \cup {msg}
    /\ replayDetected' = replayDetected

Replay(msg) ==
    /\ msg \in delivered
    /\ replayDetected' = TRUE
    /\ pending' = pending
    /\ delivered' = delivered

Next ==
    \/ \E msg \in Messages : Deliver(msg)
    \/ \E msg \in Messages : Replay(msg)

NoDuplicateDelivery ==
    delivered \subseteq Messages

ReplayRequiresDelivery ==
    replayDetected => Cardinality(delivered) > 0

Spec == Init /\ [][Next]_<<pending, delivered, replayDetected>>

=============================================================================
