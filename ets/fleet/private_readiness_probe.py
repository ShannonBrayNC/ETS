"""Private-network readiness probe for the live Fleet C3D substrate."""

from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class FleetPrivateReadinessError(RuntimeError):
    """The private Fleet readiness contract was unavailable or overclaimed."""


def main() -> None:
    base_url = _required_env("ETS_FLEET_INTERNAL_BASE_URL").rstrip("/")
    if not base_url.startswith("https://"):
        raise FleetPrivateReadinessError("Fleet private readiness URL must use HTTPS")
    request = Request(
        f"{base_url}/fleet/readyz",
        headers={"Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=10.0) as response:
            status = response.status
            payload = json.loads(response.read(64 * 1024).decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise FleetPrivateReadinessError(
            "Fleet private readiness request failed closed"
        ) from exc
    if status != 200 or not isinstance(payload, dict):
        raise FleetPrivateReadinessError("Fleet private readiness response is invalid")

    expected_true = ("ready", "process_ready", "auth_config_ready", "store_ready")
    if any(payload.get(name) is not True for name in expected_true):
        raise FleetPrivateReadinessError("Fleet private readiness dimensions are not ready")
    if payload.get("evidence_verified") is not False:
        raise FleetPrivateReadinessError("readiness may not assert evidence verification")
    if payload.get("health_asserted") is not False:
        raise FleetPrivateReadinessError("readiness may not assert device health")

    print(
        json.dumps(
            {
                "schema_version": "ets.fleet.c3d.private_readiness.v1",
                "ready": True,
                "process_ready": True,
                "auth_config_ready": True,
                "store_ready": True,
                "evidence_verified": False,
                "health_asserted": False,
            },
            sort_keys=True,
        )
    )


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise FleetPrivateReadinessError(f"{name} is required")
    return value.strip()


if __name__ == "__main__":
    main()
