---------------------- MODULE ETSLivenessProgressSymbolic ----------------------
EXTENDS Naturals, TLC

(***************************************************************************)
(* Symbolic-safe bounded liveness progress model.                           *)
(*                                                                         *)
(* This model does not attempt full temporal liveness theorem proving.      *)
(* Instead, it converts an ETS liveness concern into a bounded progress     *)
(* safety monitor suitable for SMT-backed symbolic checking.                *)
(*                                                                         *)
(* Research boundary:                                                       *)
(* - proves bounded progress-state constraints only;                        *)
(* - does not prove universal eventual convergence;                         *)
(* - does not model arbitrary Byzantine scheduling.                         *)
(***************************************************************************)

CONSTANT MaxRounds

VARIABLES round, pending, delivered, terminal

TypeOK ==
    /\ round \in 0..MaxRounds
    /\ pending \in BOOLEAN
    /\ delivered \in BOOLEAN
    /\ terminal \in BOOLEAN

Init ==
    /\ round = 0
    /\ pending = TRUE
    /\ delivered = FALSE
    /\ terminal = FALSE

Deliver ==
    /\ pending
    /\ pending' = FALSE
    /\ delivered' = TRUE
    /\ terminal' = TRUE
    /\ round' = round

Defer ==
    /\ pending
    /\ round < MaxRounds
    /\ round' = round + 1
    /\ pending' = pending
    /\ delivered' = delivered
    /\ terminal' = terminal

Timeout ==
    /\ pending
    /\ round = MaxRounds
    /\ pending' = FALSE
    /\ delivered' = delivered
    /\ terminal' = TRUE
    /\ round' = round

StutterTerminal ==
    /\ terminal
    /\ UNCHANGED <<round, pending, delivered, terminal>>

Next ==
    \/ Deliver
    \/ Defer
    \/ Timeout
    \/ StutterTerminal

Spec == Init /\ [][Next]_<<round, pending, delivered, terminal>>

BoundedProgress ==
    round = MaxRounds => terminal

DeliveredImpliesTerminal ==
    delivered => terminal

NoPendingTerminalOverlap ==
    terminal => ~pending

=============================================================================
