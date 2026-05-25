from __future__ import annotations

import hashlib

from ets.federation.identity_contracts import SignedExecutionRequest


class SignatureVerifier:
    def verify(self, request: SignedExecutionRequest) -> bool:
        expected = hashlib.sha256(
            f'{request.execution_id}:{request.payload_hash}'.encode('utf-8')
        ).hexdigest()

        return expected == request.signature
