-------------------------- MODULE ETSAsyncNetwork --------------------------
EXTENDS Naturals, Sequences, FiniteSets, TLC

CONSTANT Nodes, MaxDelay

VARIABLES queue, delivered, lost

Message == [sender: Nodes, recipient: Nodes, delay: 0..MaxDelay]

TypeOK ==
    /\ queue \in Seq(Message)
    /\ delivered \subseteq Message
    /\ lost \subseteq Message

Init ==
    /\ queue = << >>
    /\ delivered = {}
    /\ lost = {}

Enqueue(sender, recipient, delay) ==
    /\ sender \in Nodes
    /\ recipient \in Nodes
    /\ delay \in 0..MaxDelay
    /\ queue' = Append(queue, [sender |-> sender, recipient |-> recipient, delay |-> delay])
    /\ UNCHANGED <<delivered, lost>>

Tick ==
    /\ Len(queue) > 0
    /\ LET m == Head(queue) IN
        /\ queue' = Tail(queue)
        /\ delivered' = delivered \cup {m}
        /\ UNCHANGED lost

DeliverAt(i) ==
    /\ i \in DOMAIN queue
    /\ LET m == queue[i] IN
        /\ queue' = SubSeq(queue, 1, i - 1) \o SubSeq(queue, i + 1, Len(queue))
        /\ delivered' = delivered \cup {m}
        /\ UNCHANGED lost

Drop ==
    /\ Len(queue) > 0
    /\ LET m == Head(queue) IN
        /\ queue' = Tail(queue)
        /\ lost' = lost \cup {m}
        /\ UNCHANGED delivered

DropAt(i) ==
    /\ i \in DOMAIN queue
    /\ LET m == queue[i] IN
        /\ queue' = SubSeq(queue, 1, i - 1) \o SubSeq(queue, i + 1, Len(queue))
        /\ lost' = lost \cup {m}
        /\ UNCHANGED delivered

Next ==
    \/ \E sender, recipient \in Nodes, delay \in 0..MaxDelay :
        Enqueue(sender, recipient, delay)
    \/ Tick
    \/ \E i \in DOMAIN queue : DeliverAt(i)
    \/ Drop
    \/ \E i \in DOMAIN queue : DropAt(i)

NoMessageBothDeliveredAndLost == delivered \cap lost = {}

BoundedDelayQueue == \A i \in DOMAIN queue : queue[i].delay \leq MaxDelay

EventualQueueDisposition == Len(queue) > 0 ~> Len(queue) = 0

Spec == Init /\ [][Next]_<<queue, delivered, lost>>

FairSpec ==
    Spec
    /\ WF_<<queue, delivered, lost>>(Tick)
    /\ WF_<<queue, delivered, lost>>(Drop)

THEOREM Spec => []TypeOK
=============================================================================
