from hashlib import sha256

from ets.federation.identity_contracts import SignedExecutionRequest
from ets.federation.signature_verifier import SignatureVerifier
from ets.federation.trust_federation import TrustFederation


def test_trust_federation_identity() -> None:
    federation = TrustFederation()

    identity = federation.issue_identity(
        display_name='Christina',
        role='governance',
        workspace_id='opshelm',
    )

    assert identity.trust_score == 1.0


def test_signed_execution_verification() -> None:
    payload_hash = 'payload-001'

    signature = sha256(
        f"exec-001:{payload_hash}".encode()
    ).hexdigest()

    request = SignedExecutionRequest(
        execution_id='exec-001',
        actor_identity_id='identity-001',
        payload_hash=payload_hash,
        signature=signature,
    )

    verifier = SignatureVerifier()

    assert verifier.verify(request) is True
