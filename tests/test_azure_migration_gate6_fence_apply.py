from __future__ import annotations

import inspect
from pathlib import Path

import pytest
import scripts.azure_migration_gate6_fence_apply as fence
from scripts.azure_migration_control import MigrationControlError

WORKFLOW = Path(".github/workflows/azure-migration-gate6-source-fence-apply.yml")


def _preflight() -> dict[str, object]:
    return {
        "source_apps": {
            "core": {
                "name": "ets-source-api",
                "active_replica_count": 1,
                "active_revisions": [{"name": "ets-source-api--rev-a"}],
            },
            "gateway": {
                "name": "ets-source-gw",
                "active_replica_count": 1,
                "active_revisions": [{"name": "ets-source-gw--rev-a"}],
            },
        }
    }


def _state(next_index: int = 49) -> dict[str, object]:
    return {
        "table": {
            "next_index": next_index,
            "entity_count": 1 + (2 * next_index),
            "metadata_digest": "a" * 64,
            "pair_digests": [f"digest-{index}" for index in range(next_index)],
        },
        "gateway": {
            "files": [
                {"path": "gateway-sync.db", "size": 100, "sha256": "b" * 64},
            ],
            "file_count": 1,
            "total_bytes": 100,
        },
    }


def test_fence_rejects_missing_authorization_before_any_azure_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    def fail_if_called(*_args: object, **_kwargs: object) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(fence, "verify_context", fail_if_called)

    with pytest.raises(MigrationControlError, match="authorization phrase"):
        fence.apply_source_fence(
            resource_group="rg-source",
            expected_tenant="tenant",
            expected_subscription="subscription",
            authorization="wrong",
        )

    assert called is False


def test_fence_applies_monotonic_sequence_and_requires_stability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple[str, ...]] = []
    states = iter([_state(), _state()])

    monkeypatch.setattr(fence, "verify_context", lambda *_args: None)
    monkeypatch.setattr(fence, "capture_preflight", lambda *_args: _preflight())
    monkeypatch.setattr(
        fence,
        "_assert_no_scale_rules",
        lambda _rg, app: events.append(("scale", app)),
    )
    monkeypatch.setattr(
        fence,
        "_disable_ingress",
        lambda _rg, app: events.append(("ingress", app)),
    )
    monkeypatch.setattr(
        fence,
        "_deactivate_revision",
        lambda _rg, app, rev: events.append(("deactivate", app, rev)),
    )
    monkeypatch.setattr(
        fence,
        "_verify_dark",
        lambda _rg, app: events.append(("dark", app)),
    )
    monkeypatch.setattr(fence, "_capture_state", lambda _rg: next(states))

    sleeps: list[float] = []
    result = fence.apply_source_fence(
        resource_group="rg-source",
        expected_tenant="tenant",
        expected_subscription="subscription",
        authorization=fence.AUTHORIZATION_PHRASE,
        drain_seconds=5,
        stability_seconds=10,
        sleeper=sleeps.append,
    )

    assert events == [
        ("scale", "ets-source-api"),
        ("scale", "ets-source-gw"),
        ("ingress", "ets-source-gw"),
        ("ingress", "ets-source-api"),
        ("deactivate", "ets-source-gw", "ets-source-gw--rev-a"),
        ("deactivate", "ets-source-api", "ets-source-api--rev-a"),
        ("dark", "ets-source-gw"),
        ("dark", "ets-source-api"),
    ]
    assert sleeps == [5.0, 10.0]
    assert result["source_fenced"] is True
    assert result["final_copy"] is False
    assert result["destination_write_performed"] is False
    assert result["automatic_source_rollback_performed"] is False


def test_fence_blocks_when_post_fence_state_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    states = iter([_state(49), _state(50)])

    monkeypatch.setattr(fence, "verify_context", lambda *_args: None)
    monkeypatch.setattr(fence, "capture_preflight", lambda *_args: _preflight())
    monkeypatch.setattr(fence, "_assert_no_scale_rules", lambda *_args: None)
    monkeypatch.setattr(fence, "_disable_ingress", lambda *_args: None)
    monkeypatch.setattr(fence, "_deactivate_revision", lambda *_args: None)
    monkeypatch.setattr(fence, "_verify_dark", lambda *_args: None)
    monkeypatch.setattr(fence, "_capture_state", lambda _rg: next(states))

    with pytest.raises(MigrationControlError, match="changed after writer fence"):
        fence.apply_source_fence(
            resource_group="rg-source",
            expected_tenant="tenant",
            expected_subscription="subscription",
            authorization=fence.AUTHORIZATION_PHRASE,
            drain_seconds=0,
            stability_seconds=1,
            sleeper=lambda _seconds: None,
        )


def test_scale_rule_guard_rejects_event_driven_reactivation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        fence,
        "az_json",
        lambda _args: {
            "properties": {
                "template": {
                    "scale": {
                        "minReplicas": 1,
                        "maxReplicas": 1,
                        "rules": [{"name": "unexpected-event-rule"}],
                    }
                }
            }
        },
    )

    with pytest.raises(MigrationControlError, match="event-driven scale rules"):
        fence._assert_no_scale_rules("rg-source", "ets-source-api")


def test_module_has_no_automatic_source_reactivation_or_cutover_path() -> None:
    source = inspect.getsource(fence).lower()
    for forbidden in (
        '"revision",\n            "activate"',
        '"ingress",\n            "enable"',
        "az afd",
        "az network front-door",
        "role assignment create",
        "storage entity insert",
        "storage entity replace",
    ):
        assert forbidden not in source


def test_workflow_requires_exact_commit_dedicated_identity_and_authorization() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    lowered = text.lower()

    assert "workflow_dispatch:" in text
    assert "GATE6_SOURCE_WRITER_FENCE_AUTHORIZED" in text
    assert '[[ "$GITHUB_REF" == "refs/heads/main" ]]' in text
    assert '[[ "$GITHUB_SHA" == "$EXPECTED_COMMIT" ]]' in text
    assert "SOURCE_FENCE_AZURE_CLIENT_ID" in text
    assert "SOURCE_AZURE_CLIENT_ID" in text
    assert "source_fenced: `true`" in text
    assert "final_copy: `false`" in text

    for forbidden in (
        "az afd",
        "az network front-door",
        "az role assignment create",
        "az storage entity insert",
        "az storage entity replace",
        "az storage file upload",
    ):
        assert forbidden not in lowered
