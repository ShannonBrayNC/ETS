from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ETS_ROOT = REPO_ROOT / "ets"
LEGACY_PACKAGE = "ets.core.ets_core"


def test_production_code_does_not_import_legacy_core_package() -> None:
    offenders: list[str] = []

    for path in ETS_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == LEGACY_PACKAGE or alias.name.startswith(f"{LEGACY_PACKAGE}."):
                        offenders.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == LEGACY_PACKAGE or module.startswith(f"{LEGACY_PACKAGE}."):
                    offenders.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}")

    assert offenders == []


def test_canonical_packages_import() -> None:
    import ets.api.app
    import ets.core
    import ets.verifier
    import ets.verifier.cli

    assert ets.core.EvidenceEvent is not None
    assert ets.api.app.create_app is not None
    assert ets.verifier.verify_inclusion is not None
    assert ets.verifier.cli.main is not None
