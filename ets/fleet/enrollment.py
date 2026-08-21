"""Stable public facade for ETS Fleet enrollment primitives."""

from ets.fleet.models import (
    AttestationClass,
    AuthMethod,
    AuthorizationDecision,
    AuthorizationReason,
    DeviceEnrollmentRecord,
    DeviceProfile,
    EnrollmentErrorCode,
    EnrollmentValidationError,
    KeyCustody,
    ProductType,
    ProvisioningBackend,
    RegistrationState,
    RotationWindow,
    ScopeBinding,
    derive_device_id,
)
from ets.fleet.service import DeviceEnrollmentService, EnrollmentIdentityValidator
from ets.fleet.store import EnrollmentStore, InMemoryEnrollmentStore

__all__ = [
    "AttestationClass",
    "AuthMethod",
    "AuthorizationDecision",
    "AuthorizationReason",
    "DeviceEnrollmentRecord",
    "DeviceEnrollmentService",
    "DeviceProfile",
    "EnrollmentErrorCode",
    "EnrollmentIdentityValidator",
    "EnrollmentStore",
    "EnrollmentValidationError",
    "InMemoryEnrollmentStore",
    "KeyCustody",
    "ProductType",
    "ProvisioningBackend",
    "RegistrationState",
    "RotationWindow",
    "ScopeBinding",
    "derive_device_id",
]
