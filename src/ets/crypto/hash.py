import hashlib
from copy import deepcopy

from ets.canonicalization.canonicalize import canonicalize

EXCLUDED_FIELDS = {"hash", "signature"}


def prepare_for_hash(evidence: dict) -> dict:
    prepared = deepcopy(evidence)

    for field in EXCLUDED_FIELDS:
        prepared.pop(field, None)

    return prepared


def hash_evidence(evidence: dict) -> str:
    prepared = prepare_for_hash(evidence)
    canonical = canonicalize(prepared)

    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()


def verify_hash(evidence: dict) -> bool:
    expected = hash_evidence(evidence)
    return evidence.get("hash") == expected
