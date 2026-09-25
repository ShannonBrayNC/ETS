"""Public application SDK facade for ETS integrations."""

from ets.sdk.client import AsyncETSClient, ETSClient
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
    EventPageV1,
    EventRecordV1,
    SDKCompatibilityV1,
    ServiceHealthV1,
    ServiceVersionV1,
)

__all__ = [
    "APPLICATION_SDK_COMPATIBILITY_V1",
    "AsyncETSClient",
    "ETSApplicationError",
    "ETSClient",
    "EventCommitReceiptV1",
    "EventPageV1",
    "EventRecordV1",
    "SDKCompatibilityV1",
    "SDKErrorCode",
    "ServiceHealthV1",
    "ServiceVersionV1",
    "append_evidence",
    "classify_api_error",
    "create_evidence",
    "get_inclusion_proof",
    "hash_evidence",
    "verify_evidence",
    "verify_inclusion_proof",
]
