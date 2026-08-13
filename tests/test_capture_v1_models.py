from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ets.capture.models import CaptureEnvelopeV1

EXAMPLE_PATH = (
    Path(__file__).parents[1]
    / "schemas"
    / "capture"
    / "v1"
    / "examples"
    / "minimal.json"
)


def example() -> dict[str, object]:
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def capture() -> CaptureEnvelopeV1:
    return CaptureEnvelopeV1.model_validate_json(EXAMPLE_PATH.read_text(encoding="utf-8"))


def test_normative_example_parses_strictly() -> None:
    parsed = capture()
    assert parsed.schema_version == "ets.capture.v1"
    assert parsed.privacy.contains_raw_evidence is False


def test_unknown_root_and_nested_fields_rejected() -> None:
    root = example()
    root["unexpected"] = True
    with pytest.raises(ValidationError):
        CaptureEnvelopeV1.model_validate_json(json.dumps(root))

    nested = example()
    source = nested["source"]
    assert isinstance(source, dict)
    source["unexpected"] = True
    with pytest.raises(ValidationError):
        CaptureEnvelopeV1.model_validate_json(json.dumps(nested))


def test_raw_evidence_true_rejected() -> None:
    value = example()
    privacy = value["privacy"]
    assert isinstance(privacy, dict)
    privacy["contains_raw_evidence"] = True
    with pytest.raises(ValidationError):
        CaptureEnvelopeV1.model_validate_json(json.dumps(value))


def test_digest_representation_required() -> None:
    value = example()
    digest = value["content_digest"]
    assert isinstance(digest, dict)
    del digest["representation"]
    with pytest.raises(ValidationError):
        CaptureEnvelopeV1.model_validate_json(json.dumps(value))


def test_scope_sequence_and_mapping_bounds() -> None:
    value = example()
    source = value["source"]
    assert isinstance(source, dict)
    source["tenant_id"] = "t" * 129
    with pytest.raises(ValidationError):
        CaptureEnvelopeV1.model_validate_json(json.dumps(value))

    value = example()
    source = value["source"]
    assert isinstance(source, dict)
    source["sequence"] = "x" * 501
    with pytest.raises(ValidationError):
        CaptureEnvelopeV1.model_validate_json(json.dumps(value))

    value = example()
    value["metadata"] = {"value": "x" * (16 * 1024)}
    with pytest.raises(ValidationError):
        CaptureEnvelopeV1.model_validate_json(json.dumps(value))


def test_naive_timestamps_rejected() -> None:
    value = example()
    value["received_at_utc"] = "2026-08-13T14:30:01"
    with pytest.raises(ValidationError):
        CaptureEnvelopeV1.model_validate_json(json.dumps(value))


@pytest.mark.parametrize(
    ("path", "key"),
    [
        ((), "schema_version"),
        (("content_digest",), "algorithm"),
        (("content_digest",), "profile"),
        (("privacy",), "contains_raw_evidence"),
    ],
)
def test_schema_required_literals_are_model_required(
    path: tuple[str, ...], key: str
) -> None:
    value = example()
    target: object = value
    for part in path:
        assert isinstance(target, dict)
        target = target[part]
    assert isinstance(target, dict)
    del target[key]
    with pytest.raises(ValidationError):
        CaptureEnvelopeV1.model_validate_json(json.dumps(value))
