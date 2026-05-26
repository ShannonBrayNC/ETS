from __future__ import annotations

import hashlib
from uuid import uuid4

from ets.federation.identity_contracts import FederatedIdentity, TrustRole


class TrustFederation:
    def issue_identity(
        self,
        display_name: str,
        role: TrustRole | str,
        workspace_id: str,
    ) -> FederatedIdentity:
        fingerprint = hashlib.sha256(f"{display_name}:{workspace_id}".encode()).hexdigest()

        return FederatedIdentity(
            identity_id=str(uuid4()),
            display_name=display_name,
            role=TrustRole(role),
            public_key_fingerprint=fingerprint,
            workspace_id=workspace_id,
            trust_score=1.0,
        )
