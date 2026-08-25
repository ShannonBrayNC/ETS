from __future__ import annotations

import json

import pytest

from ets.qualification import microsoft_rc1b_polling_matrix as matrix


def test_rc1b_polling_matrix_proves_all_public_predicates() -> None:
    result = matrix.run_rc1b_directory_drive_fault_matrix()

    assert result
    assert all(value is True for value in result.values())
    serialized = json.dumps(result, sort_keys=True)
    for forbidden in (
        matrix.TENANT_ID,
        matrix.APPLICATION_ID,
        matrix.CREDENTIAL_REF,
        matrix.CREDENTIAL_MATERIAL.decode(),
        matrix.DRIVE_ID,
        "matrix-user",
        "matrix-group",
        "matrix-item",
        "matrix-document.docx",
        "skiptoken=matrix-next",
        "deltatoken=matrix-final",
    ):
        assert forbidden not in serialized


def test_rc1b_polling_matrix_fails_closed_on_adapter_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        matrix.MicrosoftEntraDeltaAdapter,
        "normalize",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("matrix injection")),
    )

    with pytest.raises(ValueError, match="matrix injection"):
        matrix.run_rc1b_directory_drive_fault_matrix()
