----------------------------- MODULE ETSAsyncTransport -----------------------------
EXTENDS Naturals, FiniteSets, Sequences, TLC

(***************************************************************************)
(* ETSAsyncTransport models bounded asynchronous transport semantics for    *)
(* ETS verifier federation research. It focuses on message queues, delay,   *)
(* loss, replay, message reordering, topology-aware delivery, and replay     *)
(* order constraints.                                                       *)
(*                                                                         *)
(* This model does not prove Internet-scale transport correctness. It       *)
(* defines bounded safety properties that ETS transport implementations     *)
(* should preserve before stronger symbolic or probabilistic analysis is     *)
(* attempted.                                                               *)
(***************************************************************************)

CONSTANTS Nodes, MaxMessageId, MaxDelay, MaxTime, Topology

MessageIds == 1..MaxMessageId
Times == 0..MaxTime
DelayValues == 0..MaxDelay

Message == [id: MessageIds, src: Nodes, dst: Nodes, seq: MessageIds, createdAt: Times, delay: DelayValues]

VARIABLES now, inFlight, delivered, lost, replaySuspicions, reorderSuspicions

TypeOK ==
    /\ now \in Times
    /\ inFlight \subseteq Message
    /\ delivered \in Seq(Message)
    /\ lost \subseteq Message
    /\ replaySuspicions \subseteq MessageIds
    /\ reorderSuspicions \subseteq Nodes
    /\ Topology \subseteq Nodes \X Nodes

Connected(src, dst) == <<src, dst>> \in Topology

DeliveredMessageIds == {delivered[i].id : i \in DOMAIN delivered}
DeliveredSequencesFor(dst) == {delivered[i].seq : i \in DOMAIN delivered /\ delivered[i].dst = dst}

NoDuplicateDelivery ==
    \A i, j \in DOMAIN delivered : i # j => delivered[i].id # delivered[j].id

NoDeliveryWithoutTopology ==
    \A i \in DOMAIN delivered : Connected(delivered[i].src, delivered[i].dst)

NoDeliveredLostOverlap ==
    \A msg \in lost : msg.id \notin DeliveredMessageIds

ReplaySuspicionsAreJustified ==
    \A id \in replaySuspicions : id \in DeliveredMessageIds

ReorderSuspicionsAreJustified ==
    \A dst \in reorderSuspicions :
        \E i, j \in DOMAIN delivered :
            /\ i < j
            /\ delivered[i].dst = dst
            /\ delivered[j].dst = dst
            /\ delivered[i].seq > delivered[j].seq

Init ==
    /\ now = 0
    /\ inFlight = {}
    /\ delivered = << >>
    /\ lost = {}
    /\ replaySuspicions = {}
    /\ reorderSuspicions = {}

Send(id, src, dst, seq, delay) ==
    LET msg == [id |-> id, src |-> src, dst |-> dst, seq |-> seq, createdAt |-> now, delay |-> delay] IN
        /\ id \in MessageIds
        /\ src \in Nodes
        /\ dst \in Nodes
        /\ seq \in MessageIds
        /\ delay \in DelayValues
        /\ Connected(src, dst)
        /\ id \notin {m.id : m \in inFlight}
        /\ id \notin DeliveredMessageIds
        /\ msg \notin lost
        /\ inFlight' = inFlight \cup {msg}
        /\ UNCHANGED <<now, delivered, lost, replaySuspicions, reorderSuspicions>>

Deliver(msg) ==
    /\ msg \in inFlight
    /\ now >= msg.createdAt + msg.delay
    /\ inFlight' = inFlight \ {msg}
    /\ delivered' = Append(delivered, msg)
    /\ lost' = lost
    /\ replaySuspicions' = replaySuspicions
    /\ reorderSuspicions' = reorderSuspicions \cup
        {msg.dst : \E i \in DOMAIN delivered : delivered[i].dst = msg.dst /\ delivered[i].seq > msg.seq}
    /\ UNCHANGED now

Lose(msg) ==
    /\ msg \in inFlight
    /\ inFlight' = inFlight \ {msg}
    /\ lost' = lost \cup {msg}
    /\ UNCHANGED <<now, delivered, replaySuspicions, reorderSuspicions>>

Replay(id) ==
    /\ id \in DeliveredMessageIds
    /\ replaySuspicions' = replaySuspicions \cup {id}
    /\ UNCHANGED <<now, inFlight, delivered, lost, reorderSuspicions>>

AdvanceTime ==
    /\ now < MaxTime
    /\ now' = now + 1
    /\ UNCHANGED <<inFlight, delivered, lost, replaySuspicions, reorderSuspicions>>

Next ==
    \/ AdvanceTime
    \/ \E id \in MessageIds, src \in Nodes, dst \in Nodes, seq \in MessageIds, delay \in DelayValues : Send(id, src, dst, seq, delay)
    \/ \E msg \in inFlight : Deliver(msg)
    \/ \E msg \in inFlight : Lose(msg)
    \/ \E id \in MessageIds : Replay(id)

Spec == Init /\ [][Next]_<<now, inFlight, delivered, lost, replaySuspicions, reorderSuspicions>>

Safety ==
    /\ TypeOK
    /\ NoDuplicateDelivery
    /\ NoDeliveryWithoutTopology
    /\ NoDeliveredLostOverlap
    /\ ReplaySuspicionsAreJustified
    /\ ReorderSuspicionsAreJustified

THEOREM Spec => []TypeOK
=============================================================================
