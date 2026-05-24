"""Public SDK facade for local ETS integrations."""

from ets.sdk.local import (
    append_evidence,
    create_evidence,
    get_inclusion_proof,
    hash_evidence,
    verify_evidence,
    verify_inclusion_proof,
)

__all__ = [
    "append_evidence",
    "create_evidence",
    "get_inclusion_proof",
    "hash_evidence",
    "verify_evidence",
    "verify_inclusion_proof",
]
