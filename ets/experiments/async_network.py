"""Deterministic asynchronous-network experiments for ETS federation research."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NetworkConfig:
    seed: int
    min_delay_ms: int
    max_delay_ms: int
    packet_loss_probability: float
    partial_synchrony_bound_ms: int
    allow_reordering: bool = True


@dataclass(frozen=True)
class NetworkMessage:
    sender_id: str
    recipient_id: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class DeliveryRecord:
    message: NetworkMessage
    delivered: bool
    delay_ms: int | None


@dataclass(frozen=True)
class AsyncNetworkResult:
    records: list[DeliveryRecord]
    delivered_count: int
    lost_count: int
    converged_within_bound: bool
    max_observed_delay_ms: int | None
    delivery_order: list[str]


def validate_network_config(config: NetworkConfig) -> None:
    if config.min_delay_ms < 0:
        raise ValueError("min_delay_ms must be non-negative")
    if config.max_delay_ms < config.min_delay_ms:
        raise ValueError("max_delay_ms must be greater than or equal to min_delay_ms")
    if config.partial_synchrony_bound_ms < 0:
        raise ValueError("partial_synchrony_bound_ms must be non-negative")
    if not 0.0 <= config.packet_loss_probability <= 1.0:
        raise ValueError("packet_loss_probability must be between 0 and 1")


def simulate_async_broadcast(
    sender_id: str,
    recipient_ids: list[str],
    payload: dict[str, Any],
    config: NetworkConfig,
) -> AsyncNetworkResult:
    """Simulate bounded asynchronous broadcast with seeded delay and loss."""

    validate_network_config(config)
    rng = random.Random(config.seed)
    records: list[DeliveryRecord] = []

    for recipient_id in recipient_ids:
        message = NetworkMessage(
            sender_id=sender_id,
            recipient_id=recipient_id,
            payload=payload,
        )
        lost = rng.random() < config.packet_loss_probability
        delay_ms = None if lost else rng.randint(config.min_delay_ms, config.max_delay_ms)
        records.append(DeliveryRecord(message=message, delivered=not lost, delay_ms=delay_ms))

    delivered_delays = [
        record.delay_ms for record in records if record.delivered and record.delay_ms is not None
    ]
    delivery_records = [record for record in records if record.delivered]
    if config.allow_reordering:
        delivery_records = sorted(
            delivery_records,
            key=lambda record: (record.delay_ms if record.delay_ms is not None else -1),
        )
    max_observed_delay = max(delivered_delays) if delivered_delays else None
    converged = len(delivered_delays) == len(recipient_ids) and all(
        delay <= config.partial_synchrony_bound_ms for delay in delivered_delays
    )
    return AsyncNetworkResult(
        records=records,
        delivered_count=len(delivered_delays),
        lost_count=len(recipient_ids) - len(delivered_delays),
        converged_within_bound=converged,
        max_observed_delay_ms=max_observed_delay,
        delivery_order=[record.message.recipient_id for record in delivery_records],
    )
