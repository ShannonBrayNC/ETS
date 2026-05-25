namespace ETSProofs

/--
ETS bounded fairness semantics.

This module mechanizes a small but important slice of fairness reasoning:
if an action is continuously enabled inside a bounded proof obligation and
fairness supplies execution, then the resulting state must be terminal.

Research boundary:
These proofs do not establish arbitrary scheduler fairness or universal
asynchronous liveness. They formalize the consequence of explicitly supplied
fairness assumptions.
-/

inductive FairOutcome where
  | unresolved
  | executed
  | timedOut
deriving Repr, DecidableEq

structure FairState where
  enabled : Bool
  executed : Bool
  terminal : Bool
  outcome : FairOutcome
deriving Repr

/--
A fairness assumption states that if an action remains enabled,
it eventually executes or receives a timeout classification.
-/
def FairProgress (s₁ s₂ : FairState) : Prop :=
  s₁.enabled = true -> (s₂.executed = true ∨ s₂.outcome = FairOutcome.timedOut)

/--
Terminal classification rule for fair progress outcomes.
-/
def FairTerminalRule (s : FairState) : Prop :=
  (s.executed = true ∨ s.outcome = FairOutcome.timedOut) -> s.terminal = true

/--
Valid terminal states cannot remain unresolved.
-/
def FairTerminalClassified (s : FairState) : Prop :=
  s.terminal = true -> s.outcome != FairOutcome.unresolved ∨ s.executed = true

/--
Mechanized theorem:
under a supplied fairness progress assumption and terminal rule,
an enabled action reaches a terminal state.
-/
theorem fairEnabledProgressTerminates
  (s₁ s₂ : FairState)
  (hf : FairProgress s₁ s₂)
  (ht : FairTerminalRule s₂)
  (hen : s₁.enabled = true) :
  s₂.terminal = true := by

  have hp : s₂.executed = true ∨ s₂.outcome = FairOutcome.timedOut := hf hen
  exact ht hp

/--
Mechanized theorem:
if timeout classification occurs, the outcome is not unresolved.
-/
theorem timeoutIsClassified
  (s : FairState)
  (h : s.outcome = FairOutcome.timedOut) :
  s.outcome != FairOutcome.unresolved := by

  intro hbad
  rw [h] at hbad
  contradiction

/--
Mechanized theorem:
if execution occurs, fair progress has produced evidence of action completion.
-/
theorem executedImpliesFairEvidence
  (s : FairState)
  (h : s.executed = true) :
  s.executed = true ∨ s.outcome = FairOutcome.timedOut := by

  exact Or.inl h

/--
Mechanized theorem:
a terminal state satisfying fair terminal classification cannot be silently
unclassified unless execution itself is the classification evidence.
-/
theorem terminalStateHasFairClassification
  (s : FairState)
  (hc : FairTerminalClassified s)
  (ht : s.terminal = true) :
  s.outcome != FairOutcome.unresolved ∨ s.executed = true := by

  exact hc ht

/--
Research boundary theorem.

This records that the module proves consequences of explicit fairness
assumptions; it does not prove that an arbitrary real scheduler is fair.
-/
theorem fairnessProofBoundary : True := by
  trivial

end ETSProofs
