"""Stable ETS Core exception hierarchy.

Verification failures caused by untrusted evidence should normally be returned
as structured VerificationResult values. These exceptions are reserved for
programmer errors, invalid configuration, unavailable backends, resource
limits, and internal invariant failures.
"""


class ETSError(Exception):
    """Base exception for ETS Core operational and programming failures."""


class CanonicalizationError(ETSError):
    """Canonical serialization could not be completed."""


class DuplicateKeyError(CanonicalizationError):
    """A parsed JSON object contains a duplicate key."""


class UnsupportedValueError(CanonicalizationError):
    """A value is not supported by the canonicalization profile."""


class NonFiniteNumberError(UnsupportedValueError):
    """A NaN or infinite numeric value was supplied."""


class ProfileError(ETSError):
    """Base exception for protocol-profile resolution or usage failures."""


class UnknownProfileError(ProfileError):
    """The requested protocol-profile identifier is not registered."""

    def __init__(self, profile_id: str) -> None:
        self.profile_id = profile_id
        super().__init__(f"Unknown protocol profile: {profile_id}")


class ProfileConflictError(ProfileError):
    """Conflicting or ambiguous protocol-profile declarations were supplied."""


class VerificationOnlyProfileError(ProfileError):
    """Generation was requested using a verification-only profile."""

    def __init__(self, profile_id: str) -> None:
        self.profile_id = profile_id
        super().__init__(
            f"Protocol profile is verification-only and cannot generate data: "
            f"{profile_id}"
        )


class ProtocolModelError(ETSError):
    """A trusted API received an invalid protocol model."""


class ProofConstructionError(ETSError):
    """A proof could not be constructed from trusted inputs."""


class SignatureBackendError(ETSError):
    """A required cryptographic backend is unavailable or failed."""


class ResourceLimitError(ETSError):
    """A documented implementation resource limit was exceeded."""


class InternalInvariantError(ETSError):
    """An internal ETS Core invariant was violated."""


__all__ = [
    "CanonicalizationError",
    "DuplicateKeyError",
    "ETSError",
    "InternalInvariantError",
    "NonFiniteNumberError",
    "ProfileConflictError",
    "ProfileError",
    "ProofConstructionError",
    "ProtocolModelError",
    "ResourceLimitError",
    "SignatureBackendError",
    "UnknownProfileError",
    "UnsupportedValueError",
    "VerificationOnlyProfileError",
]
