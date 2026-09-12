"""Semantic verifier for ETS captive electromagnetic actuation trials.

The verifier checks internal consistency between authorization, interlocks, command state,
observations, and declared results. It does not infer physical truth from controller logs.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class ElectromagneticActuationVerificationError(ValueError):
    """Raised when a trial violates consequence-custody semantics."""


def verify_trial_semantics(trial: Mapping[str, Any]) -> bool:
    authority = _mapping(trial, "authority")
    safety = _mapping(trial, "safety_state")
    command = _mapping(trial, "command")
    result = _mapping(trial, "result")
    observations = trial.get("observations")
    if not isinstance(observations, list):
        raise ElectromagneticActuationVerificationError("observations must be an array")

    authorization = authority.get("authorization_state")
    command_state = command.get("command_state")
    safe_to_actuate = safety.get("safe_to_actuate")
    interlock_state = safety.get("interlock_state")

    if authorization == "DENIED" and command_state == "ISSUED":
        raise ElectromagneticActuationVerificationError(
            "denied authority cannot produce an issued command"
        )
    if safe_to_actuate is False and command_state == "ISSUED":
        raise ElectromagneticActuationVerificationError(
            "unsafe state cannot produce an issued command"
        )
    if interlock_state in {"OPEN", "FAULT"} and command_state == "ISSUED":
        raise ElectromagneticActuationVerificationError(
            "open/faulted interlock cannot produce an issued command"
        )

    kinds = _known_observation_kinds(observations)
    electrical = result.get("electrical_response")
    mechanical = result.get("mechanical_response")
    thermal = result.get("thermal_response")

    if electrical == "OBSERVED" and "ACTUATION_CURRENT" not in kinds:
        raise ElectromagneticActuationVerificationError(
            "observed electrical response requires a KNOWN current observation"
        )
    if mechanical == "OBSERVED" and "ARMATURE_POSITION" not in kinds:
        raise ElectromagneticActuationVerificationError(
            "observed mechanical response requires a KNOWN position observation"
        )
    if thermal == "OBSERVED" and "TEMPERATURE" not in kinds:
        raise ElectromagneticActuationVerificationError(
            "observed thermal response requires a KNOWN temperature observation"
        )

    # A command alone never establishes consequence. Rejected/aborted commands must not
    # claim downstream physical response unless independently observed and explicitly
    # represented by a different event.
    if command_state in {"REJECTED", "ABORTED"}:
        if electrical == "OBSERVED" or mechanical == "OBSERVED":
            raise ElectromagneticActuationVerificationError(
                "rejected/aborted command cannot claim downstream actuation response"
            )

    return True


def _mapping(value: Mapping[str, Any], field: str) -> Mapping[str, Any]:
    item = value.get(field)
    if not isinstance(item, Mapping):
        raise ElectromagneticActuationVerificationError(f"{field} must be an object")
    return item


def _known_observation_kinds(observations: list[Any]) -> set[str]:
    kinds: set[str] = set()
    for item in observations:
        if not isinstance(item, Mapping):
            continue
        measurement = item.get("measurement")
        if not isinstance(measurement, Mapping):
            continue
        if measurement.get("state") == "KNOWN":
            kind = item.get("kind")
            if isinstance(kind, str):
                kinds.add(kind)
    return kinds


__all__ = ["ElectromagneticActuationVerificationError", "verify_trial_semantics"]
