import pytest

from ets.experiments.probabilistic import (
    BernoulliEvidence,
    BetaPrior,
    beta_tail_probability,
    update_beta_bernoulli,
    validate_bernoulli_evidence,
    validate_beta_prior,
)


def test_validate_beta_prior_accepts_positive_values() -> None:
    validate_beta_prior(BetaPrior(alpha=1.0, beta=1.0))


def test_validate_beta_prior_rejects_non_positive_values() -> None:
    with pytest.raises(ValueError):
        validate_beta_prior(BetaPrior(alpha=0.0, beta=1.0))


def test_validate_bernoulli_evidence_accepts_counts() -> None:
    validate_bernoulli_evidence(BernoulliEvidence(successes=2, failures=1))


def test_validate_bernoulli_evidence_rejects_negative_counts() -> None:
    with pytest.raises(ValueError):
        validate_bernoulli_evidence(BernoulliEvidence(successes=-1, failures=0))


def test_update_beta_bernoulli_returns_posterior_statistics() -> None:
    posterior = update_beta_bernoulli(
        BetaPrior(alpha=1.0, beta=1.0),
        BernoulliEvidence(successes=8, failures=2),
        reliability_threshold=0.5,
    )

    assert posterior.alpha == 9.0
    assert posterior.beta == 3.0
    assert posterior.mean == pytest.approx(0.75)
    assert posterior.variance == pytest.approx((9.0 * 3.0) / ((12.0**2) * 13.0))
    assert posterior.probability_at_least_threshold > 0.9


def test_update_beta_bernoulli_rejects_invalid_threshold() -> None:
    with pytest.raises(ValueError):
        update_beta_bernoulli(
            BetaPrior(alpha=1.0, beta=1.0),
            BernoulliEvidence(successes=1, failures=0),
            reliability_threshold=1.1,
        )


def test_beta_tail_probability_handles_boundary_thresholds() -> None:
    assert beta_tail_probability(1.0, 1.0, 0.0) == 1.0
    assert beta_tail_probability(1.0, 1.0, 1.0) == 0.0


def test_beta_tail_probability_matches_uniform_tail() -> None:
    assert beta_tail_probability(1.0, 1.0, 0.25) == pytest.approx(0.75)
