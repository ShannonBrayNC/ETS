"""Public application SDK facade for ETS integrations."""

from ets.sdk.errors import ETSApplicationError, SDKErrorCode, classify_api_error
from ets.sdk.local import (
    append_evidence,
    create_evidence,
    get_inclusion_proof,
    hash_evidence,
    verify_evidence,
    verify_inclusion_proof,
)
from ets.sdk.models import (
    APPLICATION_SDK_COMPATIBILITY_V1,
    EventCommitReceiptV1,
    SDKCompatibilityV1,
)

__all__ = [
    "APPLICATION_SDK_COMPATIBILITY_V1",
    "ETSApplicationError",
    "EventCommitReceiptV1",
    "SDKCompatibilityV1",
    "SDKErrorCode",
    "append_evidence",
    "classify_api_error",
    "create_evidence",
    "get_inclusion_proof",
    "hash_evidence",
    "verify_evidence",
    "verify_inclusion_proof",
]
