# VRX Physics Curriculum — Phase 3 Review Gate

## Scope

Phase 3 adds:

- Episode 4 — **Where Did the Energy Go?**
- Experiment 004 — **Follow the Energy**

The phase extends the accepted measurement, mechanics, and kinematics baseline into energy accounting.

## Core teaching objectives

The learner should be able to distinguish:

- power from energy;
- force from work;
- instantaneous kinetic energy from total mechanical work;
- electrical input from useful mechanical output;
- efficiency from residual;
- conservation of energy from complete observability of energy;
- physical consistency from cryptographic integrity.

## Required equations

\[
P(t)=V(t)I(t)
\]

\[
E_{electrical}=\int V(t)I(t)\,dt
\]

\[
W=\int F\,dx
\]

\[
K=\frac12mv^2
\]

\[
\eta=\frac{E_{useful}}{E_{input}}
\]

## Review questions

1. Does the lecture clearly distinguish energy conservation from measurement completeness?
2. Is the system-boundary concept introduced before efficiency is calculated?
3. Does the experiment avoid double-counting kinetic energy and mechanical work?
4. Are thermal quantities described conservatively when thermal mass/heat capacity are not characterized?
5. Are raw voltage, current, force, position, temperature, and timestamps preserved separately from derived energy quantities?
6. Is the numerical integration method required to be documented and versioned?
7. Is timestamp/synchronization quality treated as part of the measurement model?
8. Is a nonzero residual reported as a residual rather than as lost or missing energy?
9. Are PASS, FAIL, and INCONCLUSIVE outcomes defined without demanding perfect ledger closure?
10. Can an independent verifier recompute the energy ledger from retained evidence?

## Evidence Architecture proposition

Phase 3 introduces a third consistency layer alongside artifact integrity and semantic validity:

> **Physical consistency asks whether preserved measurements and derived claims can coexist under the governing physical constraints, within the declared uncertainty and model.**

A cryptographically intact artifact can still contain a physically implausible claim.

## Safety review

This phase remains within the accepted VRX-R0 envelope:

- low voltage;
- current limited;
- enclosed;
- mechanically captive;
- bounded stroke;
- manufacturer-rated operation;
- no free-launching mass or projectile;
- no maximum-output testing required.

## Acceptance gate

Phase 3 should be accepted only when:

- [ ] physics equations and terminology are correct;
- [ ] ledger terms do not double-count energy;
- [ ] system-boundary rules are explicit;
- [ ] experiment 004 is reproducible from the written protocol;
- [ ] residual terminology is scientifically defensible;
- [ ] evidence claims do not exceed instrumented observability;
- [ ] independent-verifier questions are sufficient to challenge the analysis;
- [ ] safety scope remains captive and bounded.

After acceptance, proceed to Episode 5 and Experiment 005: momentum, impulse, stopping time, and low-energy rigid-versus-compliant terminal response.