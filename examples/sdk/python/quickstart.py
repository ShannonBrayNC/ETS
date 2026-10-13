"""ETS Application SDK local developer quickstart."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from ets.core import canonical_sha256
from ets.sdk import ETSClient
from ets.verifier.service import VerifierPolicy


def main() -> None:
    event_id = f"evt_{uuid4().hex}"
    representation = {"message": "hello ETS", "sequence": 1}

    with ETSClient(
        "http://127.0.0.1:8000",
        tenant_id="dev-tenant",
        workspace_id="default",
        allow_insecure_http=True,
    ) as ets:
        version = ets.check_compatibility()
        receipt = ets.capture(
            {
                "event_id": event_id,
                "tenant_id": "dev-tenant",
                "workspace_id": "default",
                "evidence_id": f"evidence_{event_id}",
                "event_type": "sdk.quickstart",
                "subject_ref": "hello-world",
                "content_hash": canonical_sha256(representation),
                "content_hash_alg": "sha256",
                "metadata": {"representation": "example-only; raw content is not retained"},
                "created_at_utc": datetime.now(UTC),
            }
        )
        bundle = ets.bundle(receipt.event_id)
        result = ets.verify_offline(
            bundle,
            policy=VerifierPolicy(require_tree_head_signature=False),
        )

    print(f"ETS {version.version} / API {version.api_version}")
    print(f"event_id={receipt.event_id}")
    print(f"commitment_state={receipt.commitment_state}")
    print(f"offline_valid={result.valid}")
    print(f"standing_status={result.standing_status}")


if __name__ == "__main__":
    main()
