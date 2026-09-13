# VRX Physics Curriculum — Phase 02: Kinematics and Event History

**Status:** Draft complete; ready for technical review  
**PR:** #744  
**Scope:** Episode 3 and Experiment 003

## Added in this phase

- `episodes/03-motion-has-a-history.md`
  - position and displacement
  - average and instantaneous velocity
  - acceleration
  - constant-acceleration assumptions
  - sampling rate and temporal resolution
  - discrete numerical differentiation
  - noise amplification
  - raw vs filtered vs derived data
  - overshoot, stall, reversal, settling, and event segmentation
  - timestamp provenance and cross-sensor clock alignment
  - final-state vs event-history evidence

- `experiments/003-reconstruct-the-motion.md`
  - pre-registered trajectory predictions
  - bounded captive test procedure
  - raw sample schema
  - analysis provenance requirements
  - required kinematic metrics
  - terminal-state-only acceptance model
  - trajectory-aware acceptance model
  - independent-verifier questions
  - evidence-object candidates

## Central proposition

\[
\text{Resulting state evidence} \neq \text{event-history evidence}
\]

A terminal measurement can establish that the carriage ended within a defined position tolerance, subject to measurement uncertainty. It cannot by itself establish that the carriage remained within an allowed travel envelope, avoided overshoot or reversal, moved continuously, or followed an acceptable trajectory.

## Review gate

Before Phase 03 begins, review:

1. kinematic equations and dimensional consistency;
2. treatment of discrete differentiation and noise;
3. adequacy of timestamp/data-quality provenance;
4. trajectory-aware acceptance semantics;
5. whether any evidence claim exceeds the measurement capability;
6. experiment safety boundary and captive-motion requirement.

## Recommended next phase

After acceptance, Phase 03 should implement Episode 4 — **Where Did the Energy Go?** and Experiment 004 — **Follow the Energy**.

That phase should introduce electrical input energy, mechanical work, kinetic energy, energy accounting, model residuals, and the evidentiary distinction between unobserved energy pathways and physically missing energy.
