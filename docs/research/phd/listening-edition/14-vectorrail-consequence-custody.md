# Part XIV — VectorRail: When a Command Enters the Physical World

I want to make consequence custody concrete with a deliberately simple machine.

We call it VectorRail, or V R X. VectorRail is a low-energy, captive electromagnetic actuator. Its moving element remains inside a bounded test channel. The point is not to launch anything. The point is to create a physical event that is easy to instrument and difficult to misinterpret if we preserve the evidence correctly.

Imagine that I press a control and the software reports, command completed.

What do I actually know?

I know the software reported completion. That is all.

I do not yet know that electrical energy reached the actuator. I do not know that the armature moved. I do not know that the temperature changed as expected. I do not know that the apparatus returned to a safe state. And I certainly do not know those things merely because the same controller that issued the command says they happened.

VectorRail lets us separate those propositions.

First, who was authorized to request the action?

Second, did the safety policy permit it?

Third, was the command actually issued, or was it rejected?

Fourth, did independent electrical instrumentation observe an electrical response?

Fifth, did independent position instrumentation observe physical movement?

Sixth, what thermal response was observed?

And finally, did independent evidence establish the resulting safe state?

That sequence is consequence custody.

Now consider a more interesting trial. The command is authorized. The electrical event is real. But the captive carriage is deliberately blocked by the approved test fixture. The controller might still reach the end of its command routine. Yet the evidence tells us something more precise: authority existed, the command was issued, an electrical response occurred, but the expected mechanical consequence did not.

That distinction matters far beyond this experiment.

An artificial intelligence system can say that it changed a firewall rule. A robot can say that it turned left. An industrial controller can say that it closed a valve. Ranger can say that it activated an actuator.

In every case, the question is the same. Are we preserving a log of intent, or evidence of consequence?

VectorRail also gives us a clean example of epistemic conservation.

Suppose a sensor is unavailable. We must not convert unavailable into zero. We preserve unavailable as unavailable.

Suppose two independent position sensors disagree. We do not silently choose the sensor that makes the system look correct. We preserve both observations, preserve their independence, and allow the conclusion to become contradicted or indeterminate.

That is a feature, not a failure.

Evidence Architecture is valuable precisely when reality is inconvenient.

The safety system provides another important lesson. If the enclosure interlock is open, or a required safety state is unknown, VectorRail fails closed. But the rejected event still has evidentiary value. We can preserve that an action was requested, that policy evaluated it, that the safety condition was not satisfied, and that the command was rejected.

So even when no actuation occurs, something meaningful happened in the evidence chain.

Finally, we seal the trial and verify it independently. The verifier recomputes integrity and evaluates whether the recorded propositions are semantically consistent. But even then, we remain careful with our language.

A valid cryptographic digest does not prove that a sensor told the truth. A consistent evidence package does not prove objective reality. It establishes what the identified instrumentation reported, under a documented configuration, within stated observability limits.

That boundary is central to Evidence Architecture.

VectorRail is therefore not important because electromagnetic actuation is exotic. It is important because the experiment exposes a universal machine-evidence problem in a form we can see.

Intent is not consequence.

A command is not consequence.

And a machine saying that it acted is not independent evidence that the physical world changed.

When a command crosses from software into the physical world, Evidence Architecture follows it all the way through the resulting state.
