from __future__ import annotations

import json

import pytest

from ets.qualification import microsoft_rc1c_polling_matrix as matrix


def test_rc1c_polling_fault_matrix_proves_all_public_predicates() -> None:
    result = matrix.run_rc1c_polling_fault_matrix()

    assert result
    assert all(value is True for value in result.values())
    serialized = json.dumps(result, sort_keys=True)
    for forbidden in (
        matrix.TENANT_ID,
        matrix.APPLICATION_ID,
        matrix.PUBLISHER_ID,
        matrix.RECORD_ID,
        "bounded-fixture-token",
        "matrix@example.test",
        "content-001",
        "nextpage=opaque",
    ):
        assert forbidden not in serialized


def test_rc1c_polling_fault_matrix_fails_closed_on_any_false_predicate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        matrix.MicrosoftPurviewActivityAdapter,
        "normalize",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("matrix injection")),
    )

    with pytest.raises(ValueError, match="matrix injection"):
        matrix.run_rc1c_polling_fault_matrix()
