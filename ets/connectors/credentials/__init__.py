"""ETS connector credential-provider abstraction."""

from ets.connectors.credentials.broker import CredentialBroker
from ets.connectors.credentials.local import (
    CredentialSealCodec,
    LocalCredentialRecord,
    LocalSealedCredentialProvider,
    SealedCredentialBackend,
)
from ets.connectors.credentials.models import (
    CREDENTIAL_AUDIT_SCHEMA_VERSION,
    CREDENTIAL_HEALTH_SCHEMA_VERSION,
    CREDENTIAL_METADATA_SCHEMA_VERSION,
    CREDENTIAL_REFERENCE_SCHEMA_VERSION,
    CredentialAuditEventV1,
    CredentialHealthV1,
    CredentialMetadataV1,
    CredentialReferenceV1,
    credential_reference_fingerprint,
    parse_credential_reference,
)
from ets.connectors.credentials.provider import (
    CredentialLease,
    CredentialOperationUnsupportedError,
    CredentialProvider,
    CredentialProviderError,
    CredentialProviderNotFoundError,
    CredentialResolutionError,
    MutableCredentialProvider,
)

__all__ = [
    "CREDENTIAL_AUDIT_SCHEMA_VERSION",
    "CREDENTIAL_HEALTH_SCHEMA_VERSION",
    "CREDENTIAL_METADATA_SCHEMA_VERSION",
    "CREDENTIAL_REFERENCE_SCHEMA_VERSION",
    "CredentialAuditEventV1",
    "CredentialBroker",
    "CredentialHealthV1",
    "CredentialLease",
    "CredentialMetadataV1",
    "CredentialOperationUnsupportedError",
    "CredentialProvider",
    "CredentialProviderError",
    "CredentialProviderNotFoundError",
    "CredentialReferenceV1",
    "CredentialResolutionError",
    "CredentialSealCodec",
    "LocalCredentialRecord",
    "LocalSealedCredentialProvider",
    "MutableCredentialProvider",
    "SealedCredentialBackend",
    "credential_reference_fingerprint",
    "parse_credential_reference",
]
