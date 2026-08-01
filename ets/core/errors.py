"""Stable exceptions for ETS Core programmer and configuration failures."""


class ETSError(Exception):
    """Base exception for ETS Core failures that are not verification outcomes."""


class CanonicalizationError(ETSError):
    """Canonical serialization could not be completed."""


class DuplicateKeyError(CanonicalizationError):
    """A parsed JSON object contained a duplicate key."""


class UnsupportedValueError(CanonicalizationError):
    """A value is outside the active canonicalization profile."""


class NonFiniteNumberError(UnsupportedValueError):
    """A NaN or infinite number was supplied."""


class ProfileError(ETSError):
    """Base error for profile resolution or use."""


class UnknownProfileError(ProfileError):
    """A requested profile identifier is not registered."""


class ProfileConflictError(ProfileError):
    """Contradictory profile declarations were supplied."""


class VerificationOnlyProfileError(ProfileError):
    """Generation was requested under a verification-only profile."""


class ProtocolModelError(ETSError):
    """A caller supplied an invalid protocol model to a trusted API."""


class ProofConstructionError(ETSError):
    """A proof could not be constructed from trusted inputs."""


class SignatureBackendError(ETSError):
    """A required cryptographic backend is unavailable or failed."""


class ResourceLimitError(ETSError):
    """A documented implementation resource limit was exceeded."""


class InternalInvariantError(ETSError):
    """An internal invariant was violated."""
