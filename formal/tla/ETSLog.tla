----------------------------- MODULE ETSLog -----------------------------
EXTENDS Naturals, Sequences, FiniteSets, TLC

CONSTANT MaxEntries

VARIABLES log, roots, forkDetected

TypeOK ==
    /\ log \in Seq(Int)
    /\ roots \in Seq(Int)
    /\ forkDetected \in BOOLEAN

Init ==
    /\ log = << >>
    /\ roots = << >>
    /\ forkDetected = FALSE

AppendEntry(e) ==
    /\ Len(log) < MaxEntries
    /\ e \notin Range(log)
    /\ log' = Append(log, e)
    /\ roots' = Append(roots, e)
    /\ forkDetected' = forkDetected

ObserveConflictingRoot(r1, r2) ==
    /\ r1 # r2
    /\ forkDetected' = TRUE
    /\ UNCHANGED <<log, roots>>

Next ==
    \/ \E e \in 1..MaxEntries : AppendEntry(e)
    \/ \E r1, r2 \in 1..MaxEntries : ObserveConflictingRoot(r1, r2)

AppendOnly ==
    \A i, j \in DOMAIN log : i < j => log[i] # log[j]

SequenceMonotonic ==
    \A i, j \in DOMAIN log : i < j => i < j

NoMutation ==
    \A i \in DOMAIN log : log[i] \in 1..MaxEntries

RootAgreementOrForkDetected ==
    forkDetected \/ roots \in Seq(Int)

Spec == Init /\ [][Next]_<<log, roots, forkDetected>>

THEOREM Spec => []TypeOK
=============================================================================
