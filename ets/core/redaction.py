"""Deterministic metadata redaction profiles for ETS events."""

from __future__ import annotations

from typing import Any

from ets.core.models import EvidenceEvent

REDACTION_MARKER = "[REDACTED]"
SUPPORTED_REDACTION_PROFILES = {"none", "basic_pii", "strict"}
BASIC_PII_KEYS = {
    "access_token",
    "api_key",
    "email",
    "password",
    "phone",
    "refresh_token",
    "secret",
    "ssn",
    "token",
}


def apply_redaction_profile(event: EvidenceEvent, default_profile: str = "none") -> EvidenceEvent:
    profile = event.redaction_profile or default_profile
    if profile not in SUPPORTED_REDACTION_PROFILES:
        raise ValueError(f"unsupported redaction profile: {profile}")
    if profile == "none":
        if event.redaction_profile == "none":
            return event
        return event.model_copy(update={"redaction_profile": "none"})

    redacted = _redact_value(event.metadata, profile)
    return event.model_copy(update={"metadata": redacted, "redaction_profile": profile})


def _redact_value(value: Any, profile: str) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if _is_sensitive_key(key, profile):
                redacted[key] = REDACTION_MARKER
            else:
                redacted[key] = _redact_value(item, profile)
        return redacted
    if isinstance(value, list):
        return [_redact_value(item, profile) for item in value]
    return value


def _is_sensitive_key(key: str, profile: str) -> bool:
    normalized = key.lower()
    if profile == "basic_pii":
        return normalized in BASIC_PII_KEYS
    return normalized in BASIC_PII_KEYS or any(part in normalized for part in BASIC_PII_KEYS)
