------------------------- MODULE ETSUniversalTemporalLiveness -------------------------
EXTENDS Naturals, TLC

(***************************************************************************)
(* ETSUniversalTemporalLiveness studies the strongest liveness claim ETS    *)
(* can make without becoming scientifically dishonest.                      *)
(*                                                                         *)
(* The model does NOT assert unconditional liveness under arbitrary         *)
(* adversarial scheduling. That claim is intentionally excluded.            *)
(*                                                                         *)
(* Instead, this model states a conditional universal theorem over a        *)
(* bounded ETS temporal universe:                                           *)
(*                                                                         *)
(* If time is bounded, timeout classification is enabled at the boundary,   *)
(* and weak fairness is assumed for progress actions, then every pending    *)
(* evidence state eventually becomes terminal as either resolved or         *)
(* conflicted.                                                             *)
(*                                                                         *)
(* In ETS terms: universal temporal liveness is not absolute. It is         *)
(* conditional on explicit progress assumptions.                            *)
(***************************************************************************)

CONSTANT MaxTime

VARIABLES time, pending, terminal, outcome

Outcomes == {"None", "Resolved", "Conflict", "TimeoutConflict"}

TypeOK ==
    /\ time \in 0..MaxTime
    /\ pending \in BOOLEAN
    /\ terminal \in BOOLEAN
    /\ outcome \in Outcomes

Init ==
    /\ time = 0
    /\ pending = TRUE
    /\ terminal = FALSE
    /\ outcome = "None"

AdvanceTime ==
    /\ pending
    /\ time < MaxTime
    /\ time' = time + 1
    /\ UNCHANGED <<pending, terminal, outcome>>

Resolve ==
    /\ pending
    /\ pending' = FALSE
    /\ terminal' = TRUE
    /\ outcome' = "Resolved"
    /\ UNCHANGED time

ClassifyConflict ==
    /\ pending
    /\ pending' = FALSE
    /\ terminal' = TRUE
    /\ outcome' = "Conflict"
    /\ UNCHANGED time

TimeoutClassify ==
    /\ pending
    /\ time = MaxTime
    /\ pending' = FALSE
    /\ terminal' = TRUE
    /\ outcome' = "TimeoutConflict"
    /\ UNCHANGED time

TerminalStutter ==
    /\ terminal
    /\ UNCHANGED <<time, pending, terminal, outcome>>

Next ==
    \/ AdvanceTime
    \/ Resolve
    \/ ClassifyConflict
    \/ TimeoutClassify
    \/ TerminalStutter

Spec == Init /\ [][Next]_<<time, pending, terminal, outcome>>

ConditionalUniversalLivenessSpec ==
    Spec
    /\ WF_<<time, pending, terminal, outcome>>(AdvanceTime)
    /\ WF_<<time, pending, terminal, outcome>>(Resolve)
    /\ WF_<<time, pending, terminal, outcome>>(ClassifyConflict)
    /\ WF_<<time, pending, terminal, outcome>>(TimeoutClassify)

TerminalImpliesNotPending ==
    terminal => ~pending

TerminalHasOutcome ==
    terminal => outcome # "None"

NoOutcomeWithoutTerminal ==
    outcome # "None" => terminal

EventualTerminalClassification ==
    <>(terminal)

EveryPendingStateEventuallyClassifies ==
    [](pending => <>terminal)

EveryExecutionEventuallyHasOutcome ==
    <>(outcome # "None")

=============================================================================
