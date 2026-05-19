from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_IMPORT = "ets.core.ets_core"


def test_no_runtime_legacy_core_import_strings() -> None:
    offenders: list[str] = []
    for path in (REPO_ROOT / "ets").rglob("*.py"):
        relative = path.relative_to(REPO_ROOT)
        if "legacy" in relative.parts:
            continue
        if LEGACY_IMPORT in path.read_text(encoding="utf-8"):
            offenders.append(str(relative))

    assert offenders == []
