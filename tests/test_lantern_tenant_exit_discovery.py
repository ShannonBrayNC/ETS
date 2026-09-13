from __future__ import annotations

import inspect
from pathlib import Path

import scripts.lantern_tenant_exit_discovery as discovery


def _resource(name: str, resource_type: str) -> dict[str, object]:
    return {
        "name": name,
        "type": resource_type,
        "location": "eastus",
        "tags": {"workload": "lantern-site", "secret": "must-not-survive"},
        "properties": {
            "hostName": "example.azurefd.net",
            "domainValidationState": "Approved",
            "validationProperties": {
                "validationToken": "do-not-retain",
                "expirationDate": "2026-09-20T00:00:00Z",
            },
            "accessKey": "do-not-retain",
        },
    }


def _capture(role: str, resources: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": discovery._SCHEMA,
        "role": role,
        "resource_group": "rg-source" if role == "source" else "rg-destination",
        "resources": resources,
        "public_dns": {
            "apex_a": ["1.2.3.4"],
            "apex_aaaa": [],
            "www_cname": ["custom-domains.chatgpt.site"],
            "azure_cname": ["example.azurefd.net"],
        },
    }


def test_logical_keys_cover_lantern_web_edge() -> None:
    assert (
        discovery._logical_key(
            _resource("lanternbkptest", "Microsoft.Storage/storageAccounts")
        )
        == "static_site_storage"
    )
    assert (
        discovery._logical_key(
            _resource("lantern-continuity-fd", "Microsoft.Cdn/profiles")
        )
        == "frontdoor_profile"
    )
    assert (
        discovery._logical_key(
            _resource(
                "lantern-continuity-fd/lanternprotocol-net",
                "Microsoft.Cdn/profiles/customDomains",
            )
        )
        == "custom_domain_apex"
    )


def test_sanitizer_drops_tokens_keys_and_unapproved_tags() -> None:
    sanitized = discovery._sanitize_resource(
        _resource("lantern-continuity-fd", "Microsoft.Cdn/profiles")
    )
    rendered = repr(sanitized)

    assert "example.azurefd.net" in rendered
    assert "Approved" in rendered
    assert "2026-09-20T00:00:00Z" in rendered
    assert "do-not-retain" not in rendered
    assert "accessKey" not in rendered
    assert "validationToken" not in rendered
    assert "secret" not in rendered


def test_compare_marks_source_only_web_edge_as_blocking() -> None:
    source_resources = {
        key: {"name": key, "type": "test"}
        for key in discovery._REQUIRED_SOURCE_KEYS
    }
    report = discovery.compare(
        _capture("source", source_resources),
        _capture("destination", {}),
    )

    blockers = set(report["blockers"])
    assert discovery._REQUIRED_SOURCE_KEYS <= blockers
    assert "public_dns" in blockers
    assert report["tenant_exit_ready"] is False
    assert report["mutation_performed"] is False


def test_compare_marks_destination_equivalents_destination_native() -> None:
    resources = {
        key: {"name": key, "type": "test"}
        for key in discovery._REQUIRED_SOURCE_KEYS
    }
    report = discovery.compare(
        _capture("source", resources),
        _capture("destination", resources),
    )
    rows = {row["dependency"]: row for row in report["matrix"]}

    for key in discovery._REQUIRED_SOURCE_KEYS:
        assert rows[key]["classification"] == "destination-native"
        assert rows[key]["cutover_blocker"] is False
    assert rows["public_dns"]["classification"] == "external/DNS-provider"
    assert rows["public_dns"]["cutover_blocker"] is True


def test_script_contains_no_azure_write_path() -> None:
    source = inspect.getsource(discovery).lower()

    for forbidden in (
        "az afd",
        "storage blob upload",
        "storage blob delete",
        "resource create",
        "resource update",
        "resource delete",
        "role assignment create",
        "containerapp update",
    ):
        assert forbidden not in source


def test_workflow_is_manual_read_only_and_retains_only_sanitized_report() -> None:
    workflow = Path(
        ".github/workflows/lantern-tenant-exit-discovery.yml"
    ).read_text(encoding="utf-8")
    lowered = workflow.lower()

    assert "workflow_dispatch:" in workflow
    assert "\n  push:" not in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "lantern-tenant-exit-report.json" in workflow
    assert "path: ${{ runner.temp }}/lantern-source.json" not in workflow
    assert "path: ${{ runner.temp }}/lantern-destination.json" not in workflow

    for forbidden in (
        "az afd ",
        "regenerate-validation-token",
        "route update",
        "custom-domain create",
        "storage blob upload",
        "storage blob delete",
        "resource create",
        "resource update",
        "resource delete",
        "role assignment create",
        "containerapp update",
    ):
        assert forbidden not in lowered
