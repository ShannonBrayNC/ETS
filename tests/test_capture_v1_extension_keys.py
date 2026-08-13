from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ets.capture.models import CaptureEnvelopeV1

EXAMPLE_PATH = Path(__file__).parents[1] / "schemas" / "capture" / "v1" / "examples" / "minimal.json"


def load_example() -> dict[str, object]:
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def test_extension_keys_match_schema_pattern() -> None:
    value = load_example()
    value["extensions"] = {"valid.key-1": True}
    CaptureEnvelopeV1.model_validate_json(json.dumps(value))

    value["extensions"] = {"!invalid": True}
    with pytest.raises(ValidationError):
        CaptureEnvelopeV1.model_validate_json(json.dumps(value))
