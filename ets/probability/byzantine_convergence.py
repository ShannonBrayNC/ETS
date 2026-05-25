from dataclasses import dataclass
import math


@dataclass(frozen=True)
class ConvergenceResult:
    rounds: int
    probability_of_honest_majority: float
    expected_byzantine_fraction: float
    convergence_confidence: float


class ByzantineConvergenceError(ValueError):
    pass


class ProbabilisticByzantineConvergence:
    """Bounded probabilistic Byzantine convergence mathematics."""

    def __init__(self, total_nodes: int, byzantine_nodes: int) -> None:
        if total_nodes <= 0:
            raise ByzantineConvergenceError("total_nodes must be positive")

        if byzantine_nodes < 0:
            raise ByzantineConvergenceError("byzantine_nodes cannot be negative")

        if byzantine_nodes >= total_nodes:
            raise ByzantineConvergenceError(
                "byzantine_nodes must be less than total_nodes"
            )

        self.total_nodes = total_nodes
        self.byzantine_nodes = byzantine_nodes
        self.honest_nodes = total_nodes - byzantine_nodes

    @property
    def honest_fraction(self) -> float:
        return self.honest_nodes / self.total_nodes

    @property
    def expected_byzantine_fraction(self) -> float:
        return self.byzantine_nodes / self.total_nodes

    def probability_of_honest_majority(self) -> float:
        return self.honest_fraction

    def convergence_confidence(self, rounds: int) -> float:
        if rounds <= 0:
            raise ByzantineConvergenceError("rounds must be positive")

        return 1.0 - math.pow(1.0 - self.honest_fraction, rounds)
