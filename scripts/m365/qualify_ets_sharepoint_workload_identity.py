from __future__ import annotations

import base64
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

from ets.connectors.credentials.azure_managed_identity import (
    MICROSOFT_GRAPH_CREDENTIAL_REFERENCE,
    MICROSOFT_GRAPH_DEFAULT_SCOPE,
    AzureFederatedManagedIdentityCredentialProfile,
    AzureFederatedManagedIdentityCredentialProvider,
)
from ets.connectors.credentials.models import (
    CREDENTIAL_REFERENCE_SCHEMA_VERSION,
    CredentialReferenceV1,
)

APPROVED_RESOURCE_TENANT_ID = "38ac7b7f-65e1-4a2a-8e3a-7bbe18659ebe"
APPROVED_APPLICATION_ID = "0be62a70-45b5-405d-92b6-ca0ce3af953a"
APPROVED_SHAREPOINT_HOST = "echomediaai.sharepoint.com"
APPROVED_SITE_PATH = "/sites/ETS"
APPROVED_SITE_ID = (
    "echomediaai.sharepoint.com,2604ea4c-3b40-4195-b1a8-e3d7327b7c41,"
    "9ddf1ece-7f81-4258-af25-91e06afaa682"
)
APPROVED_SITE_WEB_URL = "https://echomediaai.sharepoint.com/sites/ets"
APPROVED_GRAPH_APP_ID = "00000003-0000-0000-c000-000000000000"
APPROVED_GRAPH_ROLE = "Sites.Selected"
MANAGED_IDENTITY_CLIENT_ID_ENV = "ETS_GATEWAY_MANAGED_IDENTITY_CLIENT_ID"


def _credential_reference() -> CredentialReferenceV1:
    return CredentialReferenceV1.model_validate(
        {
            "schema_version": CREDENTIAL_REFERENCE_SCHEMA_VERSION,
            "ref": MICROSOFT_GRAPH_CREDENTIAL_REFERENCE,
        }
    )


def _decode_jwt_claims(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise RuntimeError("Microsoft Graph access token is not a JWT")
    encoded = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        payload = base64.urlsafe_b64decode(encoded.encode("ascii"))
        claims = json.loads(payload.decode("utf-8"))
    except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError("Microsoft Graph access token claims could not be decoded") from exc
    if not isinstance(claims, dict):
        raise RuntimeError("Microsoft Graph access token claims are not an object")
    return claims


def _validate_app_only_claims(claims: dict[str, Any]) -> None:
    if claims.get("tid") != APPROVED_RESOURCE_TENANT_ID:
        raise RuntimeError("Microsoft Graph token tenant does not match EchoMedia")
    app_id = claims.get("appid") or claims.get("azp")
    if app_id != APPROVED_APPLICATION_ID:
        raise RuntimeError("Microsoft Graph token application does not match ETS Gateway")
    if claims.get("scp"):
        raise RuntimeError("Microsoft Graph token unexpectedly contains delegated scopes")
    roles = claims.get("roles")
    if not isinstance(roles, list) or set(map(str, roles)) != {APPROVED_GRAPH_ROLE}:
        raise RuntimeError("Microsoft Graph token role set is not exactly Sites.Selected")
    audience = str(claims.get("aud", "")).rstrip("/")
    approved_audiences = {
        APPROVED_GRAPH_APP_ID,
        "https://graph.microsoft.com",
    }
    if audience not in approved_audiences:
        raise RuntimeError("Microsoft Graph token audience is unexpected")


def _graph_get_json(token: str, uri: str) -> dict[str, Any]:
    request = Request(
        uri,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "ets-gate2-workload-identity-qualification/1",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=20) as response:
            status = getattr(response, "status", 200)
            if status != 200:
                raise RuntimeError(f"Microsoft Graph GET returned HTTP {status}")
            body = response.read(131072)
    except HTTPError as exc:
        raise RuntimeError(f"Microsoft Graph GET returned HTTP {exc.code}") from None
    except URLError as exc:
        raise RuntimeError("Microsoft Graph GET could not reach the service") from exc
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Microsoft Graph GET returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError("Microsoft Graph GET returned an unexpected payload shape")
    return value


def _managed_identity_client_id() -> str:
    value = os.environ.get(MANAGED_IDENTITY_CLIENT_ID_ENV, "").strip()
    if not value:
        raise RuntimeError(
            f"{MANAGED_IDENTITY_CLIENT_ID_ENV} is required in the Gateway runtime"
        )
    if not os.environ.get("IDENTITY_ENDPOINT") or not os.environ.get("IDENTITY_HEADER"):
        raise RuntimeError("Azure managed identity runtime endpoint is unavailable")
    return value


def _validate_site(site: dict[str, Any]) -> None:
    if site.get("id") != APPROVED_SITE_ID:
        raise RuntimeError("Resolved SharePoint site ID is not the approved ETS site")
    web_url = str(site.get("webUrl", "")).rstrip("/").casefold()
    if web_url != APPROVED_SITE_WEB_URL.casefold():
        raise RuntimeError("Resolved SharePoint site URL is not the approved ETS site")


def _validate_drive_root(root: dict[str, Any]) -> None:
    if not root.get("id") or not isinstance(root.get("folder"), dict):
        raise RuntimeError("SharePoint default drive root metadata is incomplete")
    web_url = str(root.get("webUrl", ""))
    if not web_url or urlsplit(web_url).hostname != APPROVED_SHAREPOINT_HOST:
        raise RuntimeError("SharePoint default drive root host is unexpected")


def main() -> int:
    managed_identity_client_id = _managed_identity_client_id()
    profile = AzureFederatedManagedIdentityCredentialProfile(
        reference=MICROSOFT_GRAPH_CREDENTIAL_REFERENCE,
        managed_identity_client_id=managed_identity_client_id,
        tenant_id=APPROVED_RESOURCE_TENANT_ID,
        application_id=APPROVED_APPLICATION_ID,
        scope=MICROSOFT_GRAPH_DEFAULT_SCOPE,
    )
    provider = AzureFederatedManagedIdentityCredentialProvider((profile,))
    try:
        with provider.resolve(_credential_reference()) as lease:
            if lease.metadata.provider != "azure-federated-managed-identity":
                raise RuntimeError("Unexpected Gateway credential provider")
            token = lease.reveal().decode("ascii")
            _validate_app_only_claims(_decode_jwt_claims(token))
            site_uri = (
                "https://graph.microsoft.com/v1.0/sites/"
                f"{APPROVED_SHAREPOINT_HOST}:{APPROVED_SITE_PATH}?"
                "$select=id,webUrl"
            )
            site = _graph_get_json(token, site_uri)
            _validate_site(site)
            encoded_site_id = quote(APPROVED_SITE_ID, safe=",")
            root_uri = (
                "https://graph.microsoft.com/v1.0/sites/"
                f"{encoded_site_id}/drive/root?$select=id,webUrl,folder"
            )
            root = _graph_get_json(token, root_uri)
            _validate_drive_root(root)
            del token
    finally:
        provider.close()

    result = {
        "qualification": "pass",
        "mode": "gateway_workload_identity",
        "mutationPerformed": False,
        "managedIdentityEndpointVerified": True,
        "managedIdentityClientIdPresent": True,
        "federatedCredentialProviderVerified": True,
        "resourceTenantTokenVerified": True,
        "applicationTokenVerified": True,
        "sitesSelectedRoleClaimVerified": True,
        "exactSharePointSiteVerified": True,
        "defaultDriveRootReadVerified": True,
        "reusableCredentialRetained": False,
        "sharePointPayloadRetained": False,
    }
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
