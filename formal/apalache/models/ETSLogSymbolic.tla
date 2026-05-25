----------------------------- MODULE ETSLogSymbolic -----------------------------
EXTENDS Naturals, Sequences, FiniteSets, TLC

(***************************************************************************)
(* Symbolic-safe ETS log model.                                             *)
(*                                                                         *)
(* This model is intentionally smaller than the full TLC model so that it   *)
(* can serve as an initial Apalache target. It preserves the core safety    *)
(* question for symbolic execution: a submitted event may be appended once  *)
(* and accepted log state remains bounded and typed.                        *)
(***************************************************************************)

CONSTANT EventIds

VARIABLES log

TypeOK ==
    /\ log \in Seq(EventIds)

NoDuplicateEvents ==
    \A i, j \in DOMAIN log : i # j => log[i] # log[j]

Init ==
    log = << >>

AppendEvent(event) ==
    /\ event \in EventIds
    /\ event \notin {log[i] : i \in DOMAIN log}
    /\ log' = Append(log, event)

Next ==
    \E event \in EventIds : AppendEvent(event)

Spec == Init /\ [][Next]_log

=============================================================================
