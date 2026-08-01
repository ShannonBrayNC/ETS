"""Export the normative Evidence Object v1 JSON Schema."""

from __future__ import annotations

import json
from pathlib import Path

from ets.evidence_object import EvidenceObject

OUTPUT = Path("schemas/evidence-object/v1/evidence-object.schema.json")


def main() -> None:
    schema = EvidenceObject.model_json_schema(
        by_alias=True,
        ref_template="#/$defs/{model}",
    )
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "https://lanternprotocol.org/schemas/ets/evidence-object/v1"
    schema["title"] = "ETS Evidence Object v1"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(schema, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
