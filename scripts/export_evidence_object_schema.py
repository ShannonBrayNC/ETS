"""Export the normative Evidence Object v1 JSON Schema."""

from __future__ import annotations

import json
from pathlib import Path

from ets.evidence_object import EvidenceObject

OUTPUT = Path("schemas/evidence-object/v1/evidence-object.schema.json")
SCHEMA_ID = "https://lanternprotocol.org/schemas/ets/evidence-object/v1"


def generated_schema() -> dict[str, object]:
    """Return the reproducible normative schema artifact."""

    schema = EvidenceObject.model_json_schema(
        by_alias=True,
        ref_template="#/$defs/{model}",
    )
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = SCHEMA_ID
    return schema


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(generated_schema(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
