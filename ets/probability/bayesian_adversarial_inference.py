from dataclasses import dataclass


class BayesianInferenceError(ValueError):
    pass


@dataclass(frozen=True)
class BayesianObservation:
    likelihood_given_adversarial: float
    likelihood_given_benign: float


@dataclass(frozen=True)
class BayesianInferenceResult:
    prior_adversarial: float
    posterior_adversarial: float
    likelihood_ratio: float
    classification: str


def _validate_probability(name: str, value: float) -> None:
    if value < 0.0 or value > 1.0:
        raise BayesianInferenceError(f"{name} must be between 0 and 1")


def posterior_adversarial_probability(
    prior_adversarial: float,
    observation: BayesianObservation,
) -> float:
    """Compute posterior P(adversarial | observation) using Bayes' rule."""

    _validate_probability("prior_adversarial", prior_adversarial)
    _validate_probability(
        "likelihood_given_adversarial",
        observation.likelihood_given_adversarial,
    )
    _validate_probability(
        "likelihood_given_benign",
        observation.likelihood_given_benign,
    )

    prior_benign = 1.0 - prior_adversarial
    numerator = observation.likelihood_given_adversarial * prior_adversarial
    denominator = numerator + observation.likelihood_given_benign * prior_benign

    if denominator == 0.0:
        raise BayesianInferenceError("observation has zero total likelihood")

    return numerator / denominator


def likelihood_ratio(observation: BayesianObservation) -> float:
    _validate_probability(
        "likelihood_given_adversarial",
        observation.likelihood_given_adversarial,
    )
    _validate_probability(
        "likelihood_given_benign",
        observation.likelihood_given_benign,
    )

    if observation.likelihood_given_benign == 0.0:
        raise BayesianInferenceError("benign likelihood cannot be zero")

    return observation.likelihood_given_adversarial / observation.likelihood_given_benign


def classify_adversarial_risk(posterior: float) -> str:
    _validate_probability("posterior", posterior)

    if posterior >= 0.8:
        return "high"
    if posterior >= 0.5:
        return "elevated"
    if posterior >= 0.2:
        return "guarded"
    return "low"


def infer_adversarial_risk(
    prior_adversarial: float,
    observation: BayesianObservation,
) -> BayesianInferenceResult:
    posterior = posterior_adversarial_probability(prior_adversarial, observation)

    return BayesianInferenceResult(
        prior_adversarial=prior_adversarial,
        posterior_adversarial=posterior,
        likelihood_ratio=likelihood_ratio(observation),
        classification=classify_adversarial_risk(posterior),
    )


def sequential_inference(
    prior_adversarial: float,
    observations: list[BayesianObservation],
) -> BayesianInferenceResult:
    if not observations:
        raise BayesianInferenceError("at least one observation is required")

    posterior = prior_adversarial
    last_observation = observations[-1]

    for observation in observations:
        posterior = posterior_adversarial_probability(posterior, observation)

    return BayesianInferenceResult(
        prior_adversarial=prior_adversarial,
        posterior_adversarial=posterior,
        likelihood_ratio=likelihood_ratio(last_observation),
        classification=classify_adversarial_risk(posterior),
    )
