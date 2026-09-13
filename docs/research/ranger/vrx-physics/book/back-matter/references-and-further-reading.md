# References and Further Reading

This book is an applied laboratory course rather than a replacement for a university physics, metrology, signal-processing, or forensic-science text. The sources below provide authoritative or widely used foundations for the principles discussed in the twelve chapters.

The references are grouped by purpose. A source appearing here does not imply that it endorses ETS, Evidence Architecture, Ranger, or VRX. ETS-specific propositions and terminology are the author's synthesis built on the physical, measurement, forensic, and systems-engineering foundations cited below.

## Measurement, units, and uncertainty

**Bureau International des Poids et Mesures.** *The International System of Units (SI Brochure).* 9th edition, 2019, revised 2026. DOI: 10.59161/AUEZ1291.  
Primary reference for SI quantities, units, symbols, and the measurement language used throughout this book.

**Taylor, Barry N., and Chris E. Kuyatt.** *Guidelines for Evaluating and Expressing the Uncertainty of NIST Measurement Results.* NIST Technical Note 1297, 1994 edition. DOI: 10.6028/NIST.tn.1297.  
A practical NIST treatment of standard uncertainty, Type A and Type B evaluations, propagation of uncertainty, expanded uncertainty, and reporting.

**Joint Committee for Guides in Metrology.** *Evaluation of Measurement Data — Guide to the Expression of Uncertainty in Measurement.* JCGM 100:2008, with subsequent corrections.  
The international Guide to the Expression of Uncertainty in Measurement, commonly abbreviated GUM.

**Joint Committee for Guides in Metrology.** *International Vocabulary of Metrology — Basic and General Concepts and Associated Terms (VIM).* JCGM 200.  
Reference vocabulary for measurand, measurement result, calibration, metrological traceability, uncertainty, repeatability, reproducibility, and related concepts.

### Particularly relevant chapters

Chapters 1 through 12 all depend on measurement provenance and uncertainty. Chapter 1 should be read alongside NIST TN 1297 and the VIM before formal experimental publication.

---

## General physics foundation

**Ling, Samuel J.; Sanny, Jeff; and Moebs, William.** *University Physics, Volume 1.* OpenStax, Rice University, 2016.  
Useful sections include units and measurement, one-dimensional motion, Newton's laws, work and energy, momentum and collisions, elasticity, oscillations, waves, and sound.

**Ling, Samuel J.; Sanny, Jeff; and Moebs, William.** *University Physics, Volume 2.* OpenStax, Rice University, 2016.  
Useful sections include temperature and heat, the first law of thermodynamics, current and resistance, direct-current circuits, magnetic fields, electromagnetic induction, and inductance.

These texts are recommended because they make the underlying university-level physics freely accessible. The VRX chapters deliberately add a second question to the usual physics presentation: what evidence would justify claiming that the modeled behavior actually occurred in a particular physical run?

---

## Mechanics, oscillation, vibration, and experimental dynamics

**Inman, Daniel J.** *Engineering Vibration.* Pearson.  
A standard engineering reference for single- and multiple-degree-of-freedom vibration, damping, resonance, frequency response, and vibration isolation.

**Rao, Singiresu S.** *Mechanical Vibrations.* Pearson.  
Further treatment of vibration modeling, forced response, vibration measurement, isolation, and multi-degree-of-freedom systems.

**Ewins, D. J.** *Modal Testing: Theory, Practice and Application.* Research Studies Press / Wiley.  
Recommended when the work advances beyond the Chapter 11 event-specific source/receiver spectral ratios into formal modal testing and frequency-response-function estimation.

### Particularly relevant chapters

- Chapter 2: force, free-body reasoning, net force, and mass.
- Chapter 3: kinematics and time history.
- Chapter 5: momentum, impulse, impact, and transient response.
- Chapter 11: damping, resonance, transmissibility, and structural dynamics.

---

## Electricity, magnetism, and electromechanical energy conversion

For the introductory electricity and magnetism required by Chapters 6 through 9, *University Physics, Volume 2* provides the primary accessible foundation.

For deeper electromechanical treatment, consult a university-level electric-machinery or electromechanical-energy-conversion text that develops magnetic circuits, flux linkage, magnetic energy and co-energy, position-dependent inductance, force, saturation, and hysteresis. When using formulas such as one-half current squared times the derivative of inductance with respect to position, preserve the exact sign convention, controlled variable, linearity assumption, and magnetic-state assumptions from the chosen derivation.

**Griffiths, David J.** *Introduction to Electrodynamics.* Cambridge University Press.  
Useful for a more rigorous treatment of fields, flux, electromagnetic induction, and the physical meaning behind simplified magnetic-circuit models.

### Particularly relevant chapters

- Chapter 6: voltage, current, resistance, power, and measurement boundaries.
- Chapter 7: magnetic field, magnetic circuit intuition, nonlinear materials, and force.
- Chapter 8: empirical force-map system identification.
- Chapter 9: flux linkage, inductive transients, stored magnetic energy, and moving electromechanical coupling.

---

## Heat transfer and thermal systems

**Incropera, Frank P.; DeWitt, David P.; Bergman, Theodore L.; and Lavine, Adrienne S.** *Fundamentals of Heat and Mass Transfer.* Wiley.  
Reference for conduction, convection, thermal capacitance, transient thermal behavior, thermal resistance concepts, and the distinction between energy generation inside a body and heat transfer across a boundary.

### Particularly relevant chapter

Chapter 10 uses a lumped first-order thermal model only as a bounded approximation. Real VRX assemblies may exhibit spatial gradients and multiple thermal time constants.

---

## Signals, sampling, and spectral analysis

**Oppenheim, Alan V., and Ronald W. Schafer.** *Discrete-Time Signal Processing.* Pearson.  
Reference for sampling, aliasing, discrete-time analysis, filtering, Fourier transforms, and the consequences of processing choices.

**Bendat, Julius S., and Allan G. Piersol.** *Random Data: Analysis and Measurement Procedures.* Wiley.  
Recommended for spectral estimation, transfer-function and frequency-response estimation, coherence, random-data analysis, and uncertainty in measured dynamic systems.

### Particularly relevant chapters

- Chapter 3: finite differences, sampling, filtering, and trajectory reconstruction.
- Chapter 5: short-duration force and acceleration transients.
- Chapter 11: FFT/PSD processing, coherence, empirical spectral ratios, and the distinction between descriptive spectra and formal FRF estimation.

---

## Forensic science, physical evidence, and the book's historical bridge

**National Institute of Justice / Office of Justice Programs.** *Crime Scene Investigation: A Guide for Law Enforcement.* NCJ 243598, 2013.  
A practical guide to scene documentation, processing, evidence collection, preservation, and submission. It is useful context for understanding why provenance and handling are inseparable from later interpretation.

**National Institute of Standards and Technology.** *Organization of Scientific Area Committees for Forensic Science (OSAC).*  
OSAC facilitates development and implementation of technically sound forensic-science standards and guidance intended to improve validity, reliability, reproducibility, terminology, methods, reporting, evidence handling, and quality assurance.

**National Institute of Standards and Technology.** *OSAC Registry.*  
A registry of selected published and proposed forensic-science standards containing minimum requirements, best practices, protocols, terminology, and related guidance intended to promote valid, reliable, and reproducible forensic results.

**National Research Council.** *Strengthening Forensic Science in the United States: A Path Forward.* National Academies Press, 2009.  
An important modern reference on scientific foundations, validation, standards, uncertainty, quality, and limitations in forensic practice.

### Locard's Exchange Principle

The preface uses the historically influential forensic idea commonly summarized as **"every contact leaves a trace"** as an intellectual bridge, not as a literal universal law of physics. Contact can produce transferred material, deformation, thermal change, optical change, digital state change, vibration, residue, or other consequences, but a particular trace may be absent, below detection threshold, non-unique, altered, or ambiguous.

The extension proposed in this book is:

**Traditional forensic question:** What physical trace remains after the event, and what can science infer from it?

**Instrumented Evidence Architecture question:** What observations can be captured during the event, how did the consequence propagate, what state resulted, and can an independent verifier reconstruct the claim without relying solely on the actor's own account?

That extension is a conceptual framework developed in this work; it should not be attributed to forensic-science standards bodies or to Locard himself.

---

## Accessible introductory forensic-physics context

The original discussion that motivated the expanded preface also referenced accessible online overviews describing how mechanics, matter, energy, optics, imaging, and trace properties contribute to forensic analysis. Such sources can be useful for public-facing orientation, but the formal technical foundation of this edition relies preferentially on primary standards bodies, government guidance, metrology references, and established physics/engineering texts.

Examples of introductory context include:

- SimplyForensic, material on physics in forensic science.
- ForensicSpot, introductory material on forensic physics.

These are included as context for the origin of the discussion, not as controlling technical authorities for the VRX experiments.

---

## Evidence Architecture and ETS-specific research

The following concepts are developed within the ETS / Lantern Protocol research program and should be cited to the applicable ETS technical manual, Evidence Architecture manual, experiment package, or immutable repository version when used externally:

- Evidence Object model.
- Evidence Graph model.
- Evidence plane versus control plane.
- Consequence custody.
- Physical-consistency checks as a complement to cryptographic and semantic integrity.
- State lineage across sequential cyber-physical actions.
- Force-map provenance and fail-closed model-domain semantics.
- Full-chain independent verification from authority through external consequence.
- VRX-R0 as a captive cyber-physical Evidence Architecture laboratory.
- Ranger as a platform for independently verifiable sensor-to-action-to-result provenance.

Publication citations should include the repository commit, release, DOI, archival identifier, or other immutable publication reference available at the time of publication.

---

## Recommended reading sequence

For a reader who wants to deepen the material without taking a full physics sequence:

1. BIPM SI Brochure sections on SI units and quantity notation.
2. NIST TN 1297 sections on uncertainty and reporting.
3. OpenStax *University Physics, Volume 1*: measurement, motion, Newton's laws, work/energy, momentum, and oscillations.
4. OpenStax *University Physics, Volume 2*: temperature/thermodynamics, current/resistance, magnetism, induction, and inductance.
5. Oppenheim and Schafer for sampling and signal-processing foundations.
6. Inman or Rao for vibration and isolation.
7. Bendat and Piersol before making formal frequency-response or coherence claims from experimental vibration data.
8. NIJ crime-scene guidance and the NIST OSAC materials for evidence handling, reporting, standards, reproducibility, and forensic-science context.
9. The ETS Evidence Architecture technical materials for the cyber-physical evidence framework that this book applies to VRX and Ranger.

---

## Source links for the research edition

- BIPM SI Brochure: https://www.bipm.org/en/publications/si-brochure
- NIST Technical Note 1297: https://www.nist.gov/pml/nist-technical-note-1297
- OpenStax University Physics Volume 1: https://openstax.org/books/university-physics-volume-1/pages/1-introduction
- OpenStax University Physics Volume 2: https://openstax.org/books/university-physics-volume-2/pages/1-introduction
- NIJ/OJP Crime Scene Investigation guide: https://www.ojp.gov/library/publications/crime-scene-investigation-guide-law-enforcement
- NIST OSAC: https://www.nist.gov/osac
- NIST OSAC Registry: https://www.nist.gov/osac/registry

Web resources and standards registries can change. The publication build should preserve an access date or archival reference when the final public edition is frozen.