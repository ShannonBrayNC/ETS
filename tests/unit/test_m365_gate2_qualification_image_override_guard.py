from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WRAPPER = ROOT / "scripts" / "m365" / "invoke-ets-sharepoint-workload-identity-isolated-job.ps1"
RUNBOOK = ROOT / "docs" / "migration" / "m365-gate2-isolated-runtime-job.md"
TEXT = WRAPPER.read_text(encoding="utf-8")
DOC = RUNBOOK.read_text(encoding="utf-8")

APPROVED_PREFIX = "etsprod7c8ab70380.azurecr.io/ets/hosted-q1@sha256:"
PUBLISHED_DIGEST = "945cb61c5dfe34a5ba5aefd19b101137cb9701c5f49e66f513455f80789b1de6"


def test_qualification_override_is_explicit_and_immutable() -> None:
    assert "[string]$QualificationImage = ''" in TEXT
    assert APPROVED_PREFIX.replace(".", "\\.") in TEXT
    assert "[0-9a-f]{64}$" in TEXT
    assert "QualificationImage must be an immutable sha256 reference" in TEXT


def test_qualification_override_cannot_escape_approved_registry_or_repository() -> None:
    assert "etsprod7c8ab70380\\.azurecr\\.io/ets/hosted-q1@sha256:" in TEXT
    assert "QualificationImage" in TEXT
    assert "registry-password" not in TEXT
    assert "az containerapp update" not in TEXT.lower()
    assert "az containerapp revision" not in TEXT.lower()


def test_override_only_changes_temporary_job_image_selection() -> None:
    assert "$gatewayConfiguredImage = [string]$gatewayContainer.image" in TEXT
    assert "$image = '$qualificationImageLiteral'" in TEXT
    assert "$image = $gatewayConfiguredImage" in TEXT
    assert (
        "Temporary qualification job image does not match the immutable "
        "qualification image"
        in TEXT
    )
    assert "productionGatewayImageMutationPlanned = $false" in TEXT
    assert "productionGatewayImageMutationPerformed = $false" in TEXT


def test_wrapper_does_not_forward_wrapper_only_override_to_core_parameter_binding() -> None:
    assert "$forwardParameters = @{}" in TEXT
    assert "if ($entry.Key -cne 'QualificationImage')" in TEXT
    assert "& $scriptBlock @forwardParameters" in TEXT
    assert "& $scriptBlock @PSBoundParameters" not in TEXT


def test_preview_and_final_evidence_record_override_boundary() -> None:
    for expected in (
        "immutableQualificationImageVerified = $true",
        "qualificationImageOverrideUsed = $qualificationImageOverrideUsed",
        "productionGatewayImageMutationPlanned = $false",
        "productionGatewayImageMutationPerformed = $false",
    ):
        assert expected in TEXT


def test_runbook_pins_successful_publication_digest_for_gate2() -> None:
    assert "34662606609" in DOC
    assert APPROVED_PREFIX + PUBLISHED_DIGEST in DOC
    assert "-QualificationImage $image" in DOC
    assert (
        "production Gateway must **not** be scaled up or have its configured "
        "image changed"
        in DOC
    )
