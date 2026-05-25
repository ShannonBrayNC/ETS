namespace ETSProofs

/--
Bounded Byzantine temporal semantics for ETS.

This module mechanizes consequences of bounded Byzantine evidence handling.
It does not prove arbitrary Byzantine consensus, Byzantine liveness, or
universal agreement under asynchronous faults.

The focus is narrower and scientifically defensible:
- Byzantine suspicion must produce classification evidence;
- terminal Byzantine classifications are not silent;
- conflict and resolution remain exclusive outcomes;
- Byzantine temporal handling converts unresolved adversarial ambiguity into
  explicit classified uncertainty.
-/

inductive ByzantineOutcome where
  | none
  | resolved
  | conflict
  | byzantineSuspected
  | timeoutConflict
deriving Repr, DecidableEq

structure ByzantineTemporalState where
  pending : Bool
  terminal : Bool
  byzantineObserved : Bool
  outcome : ByzantineOutcome
deriving Repr

/--
A Byzantine temporal classification rule says that if Byzantine behavior is
observed while a state remains pending, the next state must become terminal
with an adversarial classification.
-/
def ByzantineClassificationRule (s₁ s₂ : ByzantineTemporalState) : Prop :=
  s₁.pending = true ->
  s₁.byzantineObserved = true ->
  s₂.terminal = true ∧
    (s₂.outcome = ByzantineOutcome.byzantineSuspected ∨
     s₂.outcome = ByzantineOutcome.conflict ∨
     s₂.outcome = ByzantineOutcome.timeoutConflict)

/--
A valid terminal Byzantine state cannot remain pending.
-/
def ValidByzantineTerminal (s : ByzantineTemporalState) : Prop :=
  s.terminal = true -> s.pending = false

/--
A terminal Byzantine state must have an explicit classification.
-/
def ClassifiedByzantineTerminal (s : ByzantineTemporalState) : Prop :=
  s.terminal = true -> s.outcome != ByzantineOutcome.none

/--
Mechanized theorem:
if Byzantine behavior is observed in a pending state and the classification
rule applies, the successor state is terminal.
-/
theorem byzantineObservationTerminates
  (s₁ s₂ : ByzantineTemporalState)
  (rule : ByzantineClassificationRule s₁ s₂)
  (hp : s₁.pending = true)
  (hb : s₁.byzantineObserved = true) :
  s₂.terminal = true := by

  exact (rule hp hb).left

/--
Mechanized theorem:
if Byzantine behavior is observed in a pending state and the classification
rule applies, the successor outcome is adversarially classified.
-/
theorem byzantineObservationClassifies
  (s₁ s₂ : ByzantineTemporalState)
  (rule : ByzantineClassificationRule s₁ s₂)
  (hp : s₁.pending = true)
  (hb : s₁.byzantineObserved = true) :
  s₂.outcome = ByzantineOutcome.byzantineSuspected ∨
  s₂.outcome = ByzantineOutcome.conflict ∨
  s₂.outcome = ByzantineOutcome.timeoutConflict := by

  exact (rule hp hb).right

/--
Mechanized theorem:
once a Byzantine-classified successor is terminal, it cannot remain pending
under valid terminal semantics.
-/
theorem byzantineTerminalClearsPending
  (s₁ s₂ : ByzantineTemporalState)
  (rule : ByzantineClassificationRule s₁ s₂)
  (valid : ValidByzantineTerminal s₂)
  (hp : s₁.pending = true)
  (hb : s₁.byzantineObserved = true) :
  s₂.pending = false := by

  have ht : s₂.terminal = true := byzantineObservationTerminates s₁ s₂ rule hp hb
  exact valid ht

/--
Mechanized theorem:
terminal Byzantine states cannot remain silently unclassified.
-/
theorem byzantineTerminalIsClassified
  (s : ByzantineTemporalState)
  (classified : ClassifiedByzantineTerminal s)
  (ht : s.terminal = true) :
  s.outcome != ByzantineOutcome.none := by

  exact classified ht

/--
Mechanized theorem:
a resolved Byzantine temporal state is not simultaneously conflict-classified.
-/
theorem resolvedNotConflict
  (s : ByzantineTemporalState)
  (hr : s.outcome = ByzantineOutcome.resolved) :
  s.outcome != ByzantineOutcome.conflict := by

  simp [hr]

/--
Mechanized theorem:
a Byzantine-suspected state is not silently unresolved.
-/
theorem byzantineSuspicionIsNotNone
  (s : ByzantineTemporalState)
  (hb : s.outcome = ByzantineOutcome.byzantineSuspected) :
  s.outcome != ByzantineOutcome.none := by

  intro hbad
  rw [hb] at hbad
  contradiction

/--
Research boundary.

These theorems mechanize consequences of bounded Byzantine temporal
classification. They do not prove Byzantine consensus, arbitrary Byzantine
liveness, or scheduler-independent convergence.
-/
theorem byzantineTemporalProofBoundary : True := by
  trivial

end ETSProofs
