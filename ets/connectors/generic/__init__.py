"""Governed generic connector implementations and transport profiles."""

from ets.connectors.generic.extraction import (
    GenericRestAdapter,
    GenericRestExtractedPage,
    GenericRestExtractionError,
    GenericRestExtractionProfile,
    JsonObjectPointer,
    extract_generic_rest_page,
)
from ets.connectors.generic.rest import (
    GenericRestAuthenticationError,
    GenericRestAuthorizationError,
    GenericRestClientError,
    GenericRestHostPolicy,
    GenericRestHttpClient,
    GenericRestRequestProfile,
    GenericRestResponse,
    GenericRestRetryableError,
    GenericRestTerminalError,
    GenericRestThrottleError,
)

__all__ = [
    "GenericRestAdapter",
    "GenericRestAuthenticationError",
    "GenericRestAuthorizationError",
    "GenericRestClientError",
    "GenericRestExtractedPage",
    "GenericRestExtractionError",
    "GenericRestExtractionProfile",
    "GenericRestHostPolicy",
    "GenericRestHttpClient",
    "GenericRestRequestProfile",
    "GenericRestResponse",
    "GenericRestRetryableError",
    "GenericRestTerminalError",
    "GenericRestThrottleError",
    "JsonObjectPointer",
    "extract_generic_rest_page",
]
