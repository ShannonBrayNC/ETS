"""Probabilistic inference helpers for bounded ETS research experiments."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class BetaPrior:
    alpha: float
    beta: float


@dataclass(frozen=True)
class BernoulliEvidence:
    successes: int
    failures: int


@dataclass(frozen=True)
class BetaPosterior:
    alpha: float
    beta: float
    mean: float
    variance: float
    probability_at_least_threshold: float


def update_beta_bernoulli(
    prior: BetaPrior,
    evidence: BernoulliEvidence,
    reliability_threshold: float = 0.9,
) -> BetaPosterior:
    """Update a Beta prior with Bernoulli observations.

    This is a statistical research primitive for observed verifier behavior.
    It is not a proof of Byzantine correctness or real-world completeness.
    """

    validate_beta_prior(prior)
    validate_bernoulli_evidence(evidence)
    if not 0.0 <= reliability_threshold <= 1.0:
        raise ValueError("reliability_threshold must be between 0 and 1")

    alpha = prior.alpha + evidence.successes
    beta = prior.beta + evidence.failures
    total = alpha + beta
    mean = alpha / total
    variance = (alpha * beta) / ((total**2) * (total + 1.0))
    probability = beta_tail_probability(alpha, beta, reliability_threshold)
    return BetaPosterior(
        alpha=alpha,
        beta=beta,
        mean=mean,
        variance=variance,
        probability_at_least_threshold=probability,
    )


def validate_beta_prior(prior: BetaPrior) -> None:
    if not isfinite(prior.alpha) or prior.alpha <= 0:
        raise ValueError("prior alpha must be positive and finite")
    if not isfinite(prior.beta) or prior.beta <= 0:
        raise ValueError("prior beta must be positive and finite")


def validate_bernoulli_evidence(evidence: BernoulliEvidence) -> None:
    if evidence.successes < 0:
        raise ValueError("successes must be non-negative")
    if evidence.failures < 0:
        raise ValueError("failures must be non-negative")


def beta_tail_probability(alpha: float, beta: float, threshold: float) -> float:
    """Approximate P(X >= threshold) for X ~ Beta(alpha, beta).

    The deterministic midpoint integration is sufficient for small laboratory
    reports and avoids adding a SciPy dependency to the reference platform.
    """

    validate_beta_prior(BetaPrior(alpha=alpha, beta=beta))
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0 and 1")
    if threshold == 0.0:
        return 1.0
    if threshold == 1.0:
        return 0.0

    steps = 4_000
    width = (1.0 - threshold) / steps
    normalizer = _beta_function(alpha, beta)
    area = 0.0
    for index in range(steps):
        x = threshold + (index + 0.5) * width
        area += (x ** (alpha - 1.0)) * ((1.0 - x) ** (beta - 1.0)) * width
    return max(0.0, min(1.0, area / normalizer))


def _beta_function(alpha: float, beta: float) -> float:
    steps = 4_000
    width = 1.0 / steps
    area = 0.0
    for index in range(steps):
        x = (index + 0.5) * width
        area += (x ** (alpha - 1.0)) * ((1.0 - x) ** (beta - 1.0)) * width
    return area
