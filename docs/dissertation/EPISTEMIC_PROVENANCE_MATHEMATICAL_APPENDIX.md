# Advanced Mathematical Appendix — Epistemic Provenance and Bounded Evidence Claims

**Status:** research formalization appendix; candidate mathematics, not a claim of complete formal proof  
**Baseline:** synchronized to `main` at `f4e576e4fdecf032f94a69cdc67f461ea99c2272`

This appendix extends the Evidence Architecture mathematics to cover the September 2026 epistemic-provenance, prior-art, adversarial-qualification, and Ranger key-lifecycle deltas. It deliberately separates mathematical structure from stronger empirical, legal, or ontological claims.

## 1. Evidence graph with typed evidentiary relations

Let an Evidence Graph be

\[
G=(V,E,\tau,\sigma)
\]

where:

- \(V\) is the set of evidence-bearing vertices;
- \(E\subseteq V\times V\) is the directed relation set;
- \(\tau:E\rightarrow\mathcal{R}\) assigns a relation type;
- \(\sigma\) associates each vertex or edge with its support state and verification metadata.

A useful relation vocabulary is

\[
\mathcal{R}=\{OBSERVED, ASSERTED, REPORTED, DERIVED, CORROBORATES,
CONTRADICTS, INFERRED, INTERPRETED, PRECEDES, CONTRIBUTES, CAUSES,
NECESSITATES\}.
\]

The principal discipline is that graph connectivity does not imply semantic equivalence. For edges \(e_1,e_2\in E\),

\[
\tau(e_1)\neq\tau(e_2)
\]

may represent materially different epistemic claims even when the same vertices are connected.

In particular,

\[
PRECEDES \not\Rightarrow CAUSES
\]

and

\[
ASSERTED \not\Rightarrow OBSERVED.
\]

## 2. Claim support state

For a proposition \(c\), evidence package \(P\), and declared verification policy \(\theta\), define

\[
\mathcal{V}(c\mid P,\theta)\in
\{SUPPORTED, NOT\_ESTABLISHED, CONTRADICTED, INDETERMINATE\}.
\]

This is not a universal probability-of-truth function. It is a bounded verifier result under the supplied evidence and policy.

A successful cryptographic check may be one predicate inside \(\theta\), but

\[
Integrity(c)=1 \not\Rightarrow \mathcal{V}(Truth(c))=SUPPORTED.
\]

Likewise,

\[
Authentication(c)=1 \not\Rightarrow Authorization(c)=1.
\]

These are type-separation invariants rather than probabilistic claims.

## 3. Provenance does not collapse into truth

Let \(Prov(x)\) denote the proposition that the lineage of artifact or claim \(x\) verifies under the configured provenance mechanism. Let \(T(x)\) denote the proposition that the semantic content represented by \(x\) corresponds to objective reality.

The architecture requires the non-implication

\[
Prov(x) \not\Rightarrow T(x).
\]

Similarly, for cryptographic integrity \(I(x)\),

\[
I(x) \not\Rightarrow T(x).
\]

This does not assert that \(T(x)\) is false. It asserts only that the named mechanism does not, by itself, establish \(T(x)\).

## 4. Epistemic-distance vector

For evidence item \(e\) used to support claim \(c\), define a multidimensional epistemic-distance vector

\[
D(c,e)=
(\Delta_t, d_{tr}, n_{rep}, \ell_{ctx}, d_{src}, d_{inf}, u).
\]

Candidate dimensions are:

- \(\Delta_t\): temporal separation among event, observation, recording, and evaluation;
- \(d_{tr}\): transformation depth;
- \(n_{rep}\): number of intermediary reporting steps;
- \(\ell_{ctx}\): declared context loss;
- \(d_{src}\): source-dependence measure;
- \(d_{inf}\): model or analyst inference depth;
- \(u\): uncertainty representation associated with the chain.

No canonical scalar is defined.

A policy may define

\[
S_D = f_\theta(D)
\]

for some declared policy function \(f_\theta\), but the vector \(D\) must remain inspectable. A scalar derived from \(D\) must not be presented as a universal posterior probability of truth unless a valid probabilistic model is separately specified and justified.

## 5. Observability boundary

Let \(\Omega_s(t)\) denote the set of states or signals source \(s\) could observe at time \(t\) under its capability, configuration, field of view, collection policy, retention state, and availability.

For event proposition \(c\), absence of an observation \(o_c\) does not establish negation of \(c\) unless an explicit expectation model places \(c\) inside the observability boundary:

\[
\neg o_c \land c\notin\Omega_s(t)
\not\Rightarrow \neg c.
\]

Even when \(c\in\Omega_s(t)\), a negative inference may require an explicit detection model \(M_s\):

\[
\neg o_c \land c\in\Omega_s(t) \land M_s
\Rightarrow_{\theta}
\text{bounded negative support}.
\]

The implication remains policy- and model-relative.

## 6. Source independence and common-source collapse

Let \(A(x)\) be the set of upstream ancestor sources for evidentiary item \(x\).

Two reports \(x\) and \(y\) are not independent merely because \(x\neq y\). A simple dependency predicate is

\[
Dep(x,y)=1 \iff A(x)\cap A(y)\neq\varnothing.
\]

Define a dependency graph \(G_D\) whose vertices are candidate corroborating items and whose edges connect items sharing material ancestry. A conservative effective independent-source count can be based on connected components or on a stricter policy-defined partition rather than raw artifact count.

Thus,

\[
N_{artifacts} \geq N_{independent\ sources},
\]

with equality only when the independence policy is satisfied.

This construction is intentionally not a Bayesian independence claim. It is an ancestry-based evidentiary control.

## 7. Interpretation provenance

Let an interpretation event be

\[
J=(X,m,v,a,p,t,k,y)
\]

where:

- \(X\) is the set of input evidence identifiers;
- \(m\) is the method or model;
- \(v\) is its version;
- \(a\) is analyst or agent identity;
- \(p\) is parameter/policy state;
- \(t\) is time/context metadata;
- \(k\) is the set of declared assumptions;
- \(y\) is the produced conclusion.

The interpretation output \(y\) is a derived claim. Its provenance must preserve a reconstructable mapping

\[
(X,m,v,a,p,t,k)\mapsto y.
\]

Changing \(y\) or replacing the interpretation process must not mutate the underlying evidence \(X\).

## 8. Claim genealogy

For proposition family \(q\), define a genealogy graph

\[
\Gamma_q=(C_q,R_q)
\]

where \(C_q\) contains assertion instances and \(R_q\) contains relations such as copied-from, paraphrases, strengthens, weakens, corrects, retracts, contradicts, and independently-observes.

Repetition count

\[
|C_q|
\]

is not itself independent support. Ancestry must be considered before any corroboration measure is increased.

## 9. Unsupported-assumption propagation

Let \(U(x)\) denote the set of unsupported assumptions required to interpret evidentiary item or claim \(x\).

For a derived claim

\[
y=g(x_1,\ldots,x_n;k),
\]

where \(k\) is the set of new assumptions introduced by the derivation, a conservative propagation rule is

\[
U(y) \supseteq \left(\bigcup_{i=1}^{n}U(x_i)\right)\cup k.
\]

A verifier may discharge some assumptions when new evidence is supplied, but it must not silently erase them.

This gives a formal expression to the Evidence Architecture requirement that graph composition must not upgrade unsupported edges into supported truth merely because they sit inside a larger connected graph.

## 10. Historical key standing

For a publication scope \(s\), role \(r\), key \(k\), and authority-history prefix \(H_j\), define

\[
Standing(k,r,s\mid H_j)\in\{0,1\}.
\]

Let the full presented history be \(H_n\) with \(j\leq n\). Historical standing and current authorization are separate predicates:

\[
Standing(k,r,s\mid H_j)=1
\]

does not imply

\[
Current(k,r,s\mid H_n)=1.
\]

After a valid rotation or revocation, a historical record can therefore satisfy

\[
Standing(k,r,s\mid H_j)=1
\quad\land\quad
Current(k,r,s\mid H_n)=0.
\]

This preserves historical verifiability without granting present authority.

The relation is prefix-relative; it does not, by itself, prove when the source signature occurred relative to lifecycle transitions.

## 11. Freshness relative to retained state

Let \(h(P)\) be the verified head of presented history \(P\), and let \(h_R\) be a previously retained trusted head.

A verifier may define

\[
Fresh_R(P)=1
\]

when \(P\) validly extends or otherwise satisfies the configured relationship to \(h_R\).

But

\[
Fresh_R(P)=1 \not\Rightarrow GlobalLatest(P)=1.
\]

Freshness is therefore relative to the retained or independently witnessed state used by the verifier unless a stronger global-latest mechanism is explicitly configured.

## 12. Consequence-chain separation

For cyber-physical or autonomous systems, represent the chain as distinct variables:

\[
O\rightarrow I\rightarrow A\rightarrow D\rightarrow C\rightarrow X\rightarrow R,
\]

where:

- \(O\): observation;
- \(I\): interpretation or inference;
- \(A\): authority/standing state;
- \(D\): decision;
- \(C\): command/request;
- \(X\): externally meaningful execution or actuation;
- \(R\): resulting-state observation.

No adjacent implication should be assumed solely from temporal proximity. In particular,

\[
C=accepted \not\Rightarrow R=desired.
\]

The evidence graph should permit contradictory evidence at any stage.

## 13. Independent machine-action observation

Let actor-generated evidence be \(E_a\) and independently captured action-boundary evidence be \(E_w\). For a consequential action claim \(c\), the architecture prefers a verification basis

\[
\mathcal{V}(c\mid E_a\cup E_w,\theta)
\]

over a basis containing only \(E_a\) when the actor can influence its own transcript or log.

This is not a theorem that every independent observer is trustworthy. It is a trust-domain separation principle: the subject under evaluation should not be the sole authority for the evidence used to establish its own consequential actions.

## 14. Adversarial qualification result object

An EAQ run can be represented as

\[
Q=(id,auth,scope,sut,cfg,hyp,proc,obs,result,rem,reg),
\]

where the fields bind authorization, scope, system-under-test identity, configuration, hypothesis, bounded procedure, observations, result class, remediation reference, and regression evidence.

The result domain is

\[
Result(Q)\in\{PASS,FAIL,INCONCLUSIVE,BLOCKED\}.
\]

A PASS result is evidence that the tested invariant survived the stated procedure under the captured conditions. It is not universal proof that no attack exists.

## 15. Research-status boundary

The structures in this appendix are useful formalizations, but they should not be represented as completed universal mathematics unless supported by mechanized proofs, peer review, or the applicable research gate.

Specifically, this appendix does not establish:

- objective truth from provenance;
- universal probability of truth;
- complete source independence;
- global freshness;
- global authorization currentness;
- complete capture;
- physical consequence solely from command evidence;
- legal sufficiency;
- novelty of the full Evidence Object or Evidence Graph concepts.

Its role is to sharpen the mathematical vocabulary and proof obligations for the next research and manual editions.
