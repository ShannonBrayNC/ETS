import hashlib
import json

import pytest

from ets.connectors.enterprise.microsoft_maintenance_observer import (
    MaintenanceExpectation,
    observe_synthetic_maintenance_item,
)


def fixture():
    return {
        "id": "900001",
        "fields": {
            "CaseId": "demo-maintenance-001",
            "TicketId": "900001",
            "ApprovalStatus": "approved",
            "DraftSha256": hashlib.sha256(b"synthetic draft").hexdigest(),
            "OutboundCommunicationAllowed": False,
        },
    }


def expectation():
    return MaintenanceExpectation(
        item_id="900001", case_id="demo-maintenance-001", ticket_id="900001",
        draft_sha256=hashlib.sha256(b"synthetic draft").hexdigest(),
    )


def observe(value):
    return observe_synthetic_maintenance_item(
        json.dumps(value).encode(), expected=expectation(), producer_reported_success=True,
    )


def test_observed_target_binds_exact_source_and_expected_state():
    payload = json.dumps(fixture()).encode()
    result = observe_synthetic_maintenance_item(payload, expected=expectation())
    assert result.outcome == "observed"
    assert result.source_sha256 == hashlib.sha256(payload).hexdigest()
    assert all(passed for _, passed in result.assertions)
    assert result.mode == "simulated-source"
    assert result.qualified is False


@pytest.mark.parametrize("field", list(fixture()["fields"]))
def test_missing_field_cannot_be_overridden_by_producer_success(field):
    value = fixture()
    del value["fields"][field]
    assert observe(value).outcome == "unresolved"
    assert observe(fixture()).outcome == "observed"


@pytest.mark.parametrize("field,value", [
    ("CaseId", "wrong-case"), ("TicketId", "900002"),
    ("ApprovalStatus", "rejected"), ("DraftSha256", "0" * 64),
    ("OutboundCommunicationAllowed", True),
])
def test_target_contradictions_remain_visible(field, value):
    target = fixture()
    target["fields"][field] = value
    assert observe(target).outcome == "contradictory"


@pytest.mark.parametrize("payload", [
    b'{"id":"a","id":"b"}', b'{"fields":NaN}', b'[]', b'{}', b'\xff',
])
def test_malformed_source_is_unresolved(payload):
    assert observe_synthetic_maintenance_item(
        payload, expected=expectation(), producer_reported_success=True,
    ).outcome == "unresolved"


def test_wrong_types_and_deleted_target_fail_closed():
    target = fixture()
    target["fields"]["OutboundCommunicationAllowed"] = 0
    assert observe(target).outcome == "unresolved"
    target = fixture()
    target["deleted"] = {}
    assert observe(target).outcome == "contradictory"


def test_unknown_sensitive_fields_do_not_enter_minimized_result():
    target = fixture()
    target["fields"]["SecretNotes"] = "must never be retained"
    result = observe(target)
    assert result.outcome == "observed"
    assert "must never" not in repr(result)
    assert "SecretNotes" not in repr(result)


def test_oversized_source_and_invalid_expectation_are_rejected():
    with pytest.raises(ValueError, match="byte bound"):
        observe_synthetic_maintenance_item(b" " * 16385, expected=expectation())
    with pytest.raises(ValueError):
        MaintenanceExpectation(item_id="", case_id="x", ticket_id="x", draft_sha256="0" * 64)
