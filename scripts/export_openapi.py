from __future__ import annotations

import json
from pathlib import Path

from ets.api.app import create_app


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    output_path = repo_root / "docs" / "api" / "openapi.generated.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    app = create_app()
    schema = app.openapi()
    output_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
