from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "m365" / "invoke-ets-sharepoint-workload-identity-isolated-job.ps1"
TEXT = SCRIPT.read_text(encoding="utf-8")
LOWER = TEXT.lower()


def test_isolated_job_is_hard_bound_to_approved_gateway() -> None:
    required = (
        "0d20cf0f-3498-46c1-a0db-69b09c634cc2",
        "5729a82b-8850-4868-b96c-96c3805cbb9d",
        "rg-ets-prod-eastus",
        "ets-oif5r5ydprrou-gw",
        "ets-oif5r5ydprrou-gw-id",
        "ets-gateway",
        "qualify_ets_sharepoint_workload_identity.py",
    )
    for value in required:
        assert value in TEXT


def test_isolated_job_requires_explicit_apply_and_zero_gateway_runtime() -> None:
    assert "[switch]$Apply" in TEXT
    assert "if (-not $Apply)" in TEXT
    assert "activeRevisionCount" in TEXT
    assert "activeReplicaCount" in TEXT
    assert "runtimeActivationRequired" in TEXT
    assert "production Gateway to remain at zero runtime" in TEXT


def test_isolated_job_reuses_immutable_gateway_image_and_existing_identities() -> None:
    assert "@sha256:[0-9a-fA-F]{64}$" in TEXT
    assert "Gateway image registry does not match the configured ACR server" in TEXT
    assert "Gateway runtime and ACR pull identities must remain distinct" in TEXT
    assert "userAssignedIdentities" in TEXT
    assert "identitySettings" in TEXT
    assert "lifecycle = 'Main'" in TEXT
    assert "lifecycle = 'None'" in TEXT


def test_isolated_job_never_starts_gateway_or_mounts_gateway_state() -> None:
    assert "command = @('python')" in TEXT
    assert "volumeMounts = @()" in TEXT
    assert "volumes = @()" in TEXT
    assert "gatewayEntrypointStarted = $false" in TEXT
    assert "gatewayStateMounted = $false" in TEXT
    assert "ets.gateway.container_entrypoint" not in TEXT
    assert "gateway-state" not in LOWER


def test_isolated_job_is_one_shot_bounded_and_uses_direct_job_resource() -> None:
    assert "/providers/Microsoft.App/jobs/$jobName" in TEXT
    assert "triggerType = 'Manual'" in TEXT
    assert "replicaTimeout = 180" in TEXT
    assert "replicaRetryLimit = 0" in TEXT
    assert "parallelism = 1" in TEXT
    assert "replicaCompletionCount = 1" in TEXT
    assert "az rest `\n        --method put" in TEXT
    assert "az containerapp job start" in TEXT


def test_isolated_job_does_not_mutate_gateway_or_rbac() -> None:
    forbidden = (
        "az containerapp update",
        "az containerapp revision activate",
        "az containerapp revision copy",
        "az containerapp revision restart",
        "az containerapp revision set-mode",
        "az containerapp identity assign",
        "az role assignment create",
        "az role assignment delete",
        "az identity create",
        "az identity delete",
    )
    for value in forbidden:
        assert value not in LOWER
    assert "productionGatewayMutationPerformed = $false" in TEXT
    assert "azureRbacMutationPerformed = $false" in TEXT


def test_isolated_job_cleanup_is_mandatory() -> None:
    assert "finally {" in TEXT
    assert "az rest --method delete --uri $jobUri" in TEXT
    assert "temporary Gate 2 qualification job cleanup failed" in TEXT
    assert "temporary Gate 2 qualification job still exists after cleanup" in TEXT
    assert "temporaryJobDeleted = $true" in TEXT


def test_isolated_job_requires_sanitized_runtime_proof() -> None:
    required_markers = (
        '"qualification"\\s*:\\s*"pass"',
        '"federatedCredentialProviderVerified"\\s*:\\s*true',
        '"sitesSelectedRoleClaimVerified"\\s*:\\s*true',
        '"exactSharePointSiteVerified"\\s*:\\s*true',
        '"defaultDriveRootReadVerified"\\s*:\\s*true',
        '"reusableCredentialRetained"\\s*:\\s*false',
        '"sharePointPayloadRetained"\\s*:\\s*false',
    )
    for value in required_markers:
        assert value in TEXT


def test_isolated_job_does_not_print_token_or_sharepoint_payload() -> None:
    forbidden = (
        "write-host $token",
        "write-output $token",
        "convertto-json $token",
        "authorization: bearer",
    )
    for value in forbidden:
        assert value not in LOWER
    assert "reusableCredentialRetained = $false" in TEXT
    assert "sharePointPayloadRetained = $false" in TEXT
