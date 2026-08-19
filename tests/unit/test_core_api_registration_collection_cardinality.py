from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "azure" / "ensure-core-api-application.ps1"


def test_graph_collection_calls_are_wrapped_at_cardinality_sensitive_call_sites() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    application_call = "@(Get-CoreApplicationCandidates -Name $DisplayName)"
    service_principal_call = (
        "@(Get-CoreServicePrincipals -ApplicationId $application.appId)"
    )

    # PowerShell enumerates function output. Without caller-side @(...), a single
    # Graph result becomes a scalar PSCustomObject and .Count fails under StrictMode.
    assert text.count(application_call) == 3
    assert text.count(service_principal_call) == 2

    assert "$applications = Get-CoreApplicationCandidates -Name $DisplayName" not in text
    assert (
        "$servicePrincipals = Get-CoreServicePrincipals -ApplicationId $application.appId"
        not in text
    )
