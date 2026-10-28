"""Integrity and safe-output qualification for the SDK test-kit assembler."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import build_sdk_test_kit as kit

COMMIT = "a" * 40


@pytest.fixture
def fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    source = tmp_path / "source"
    for folder in kit.SOURCE_DIRS:
        (source / folder).mkdir(parents=True)
        (source / folder / "README.md").write_text("sample docs")
    for name in kit.SOURCE_FILES:
        (source / name).parent.mkdir(parents=True, exist_ok=True)
        (source / name).write_text("license or reference")
    matrix = {
        "release_tag": "v0.1.0-alpha.1",
        "sdk_contract": "ets.application.sdk.v1",
        "packages": {"python": {"version": "0.1.0a1"}},
    }
    (source / "docs/sdk/RELEASE_MATRIX.json").write_text(json.dumps(matrix))
    monkeypatch.setattr(kit, "ROOT", source)
    monkeypatch.setattr(kit, "verify_source_snapshot", lambda sources, commit: None)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    entries = []
    for name in (
        "python/example.whl",
        "python/example.tar.gz",
        "dotnet/example.nupkg",
        "dotnet/example.snupkg",
        "typescript/example.tgz",
        "sdk-release.spdx.json",
    ):
        path = artifacts / name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(name.encode())
        entries.append(
            {
                "path": name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size_bytes": path.stat().st_size,
            }
        )
    manifest = {
        "schema_version": "ets.sdk.release_manifest.v1",
        "source_commit": COMMIT,
        **matrix,
        "artifacts": entries,
    }
    (artifacts / "sdk-release-manifest.json").write_text(json.dumps(manifest))
    (artifacts / "SHA256SUMS").write_text(
        "".join(f"{entry['sha256']}  {entry['path']}\n" for entry in entries)
    )
    return source, artifacts


def test_build_and_verify_manifest_and_no_generated_files(fixture, tmp_path: Path) -> None:
    source, artifacts = fixture
    generated = source / "examples/sdk/node_modules"
    generated.mkdir()
    (generated / "secret.txt").write_text("must not ship")
    output = tmp_path / "kit"
    result = kit.build_kit(artifacts, output, commit=COMMIT)
    assert result["distribution_scope"] == "alpha-testing-only"
    assert (output / "packages/python/example.whl").exists()
    assert not (output / "examples/sdk/node_modules").exists()
    assert kit.verify_kit(output, commit=COMMIT) == result
    (output / "README.md").write_text("tampered")
    with pytest.raises(ValueError, match="hash/size mismatch"):
        kit.verify_kit(output)


@pytest.mark.parametrize("change", ["source", "hash", "missing", "extra", "checksum"])
def test_reject_bad_artifact_inputs(fixture, tmp_path: Path, change: str) -> None:
    _, artifacts = fixture
    if change == "source":
        manifest = artifacts / "sdk-release-manifest.json"
        data = json.loads(manifest.read_text())
        data["source_commit"] = "b" * 40
        manifest.write_text(json.dumps(data))
    elif change == "hash":
        (artifacts / "python/example.whl").write_text("tampered")
    elif change == "missing":
        (artifacts / "dotnet/example.nupkg").unlink()
    elif change == "extra":
        (artifacts / "unexpected.secret").write_text("do not copy")
    else:
        (artifacts / "SHA256SUMS").write_text("not the manifest")
    with pytest.raises((ValueError, FileNotFoundError)):
        kit.build_kit(artifacts, tmp_path / "kit", commit=COMMIT)
    assert not (tmp_path / "kit").exists()


@pytest.mark.parametrize("path", ["../escape", "/absolute", "foo\\bar", "C:drive", "a//b"])
def test_reject_unsafe_manifest_paths(fixture, tmp_path: Path, path: str) -> None:
    _, artifacts = fixture
    manifest = artifacts / "sdk-release-manifest.json"
    data = json.loads(manifest.read_text())
    data["artifacts"][0]["path"] = path
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="Unsafe"):
        kit.build_kit(artifacts, tmp_path / "kit", commit=COMMIT)


def test_existing_output_and_symlink_are_rejected(fixture, tmp_path: Path) -> None:
    source, artifacts = fixture
    output = tmp_path / "kit"
    output.mkdir()
    protected = output / "keep.txt"
    protected.write_text("keep")
    with pytest.raises(FileExistsError):
        kit.build_kit(artifacts, output, commit=COMMIT)
    assert protected.read_text() == "keep"
    target = source / "docs/sdk/linked.json"
    target.symlink_to(artifacts / "sdk-release-manifest.json")
    with pytest.raises(ValueError, match="Symlinks"):
        kit.build_kit(artifacts, tmp_path / "new-kit", commit=COMMIT)


def test_verify_rejects_extra_file_and_wrong_commit(fixture, tmp_path: Path) -> None:
    _, artifacts = fixture
    output = tmp_path / "kit"
    kit.build_kit(artifacts, output, commit=COMMIT)
    with pytest.raises(ValueError, match="source commit mismatch"):
        kit.verify_kit(output, commit="b" * 40)
    (output / "extra.txt").write_text("extra")
    with pytest.raises(ValueError, match="Unexpected"):
        kit.verify_kit(output)


def test_omitted_source_links_use_immutable_commit(fixture, tmp_path: Path) -> None:
    source, artifacts = fixture
    guide = source / "docs/sdk/README.md"
    guide.write_text(
        "[bundled](RELEASE_MATRIX.json) [source](../../ets/sdk/client.py#methods) "
        "[external](https://example.com/guide) [fragment](#local)"
    )
    output = tmp_path / "kit"
    kit.build_kit(artifacts, output, commit=COMMIT)
    text = (output / "docs/sdk/README.md").read_text()
    assert "[bundled](RELEASE_MATRIX.json)" in text
    assert f"https://github.com/ShannonBrayNC/ETS/blob/{COMMIT}/ets/sdk/client.py#methods" in text
    assert "[external](https://example.com/guide)" in text
    assert "[fragment](#local)" in text
    kit.verify_kit(output, commit=COMMIT)


def test_markdown_link_cannot_escape_repository(fixture, tmp_path: Path) -> None:
    source, artifacts = fixture
    (source / "docs/sdk/README.md").write_text("[escape](../../../outside.txt)")
    with pytest.raises(ValueError, match="escapes repository"):
        kit.build_kit(artifacts, tmp_path / "kit", commit=COMMIT)


def test_source_snapshot_rejects_wrong_head_and_modified_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    source = tmp_path / "git-source"
    source.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=source, check=True)
    document = source / "guide.md"
    document.write_text("committed")
    subprocess.run(["git", "add", "guide.md"], cwd=source, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=SDK Test",
            "-c",
            "user.email=sdk-test@example.invalid",
            "commit",
            "-qm",
            "test snapshot",
        ],
        cwd=source,
        check=True,
    )
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=source, check=True, capture_output=True, text=True
    ).stdout.strip()
    monkeypatch.setattr(kit, "ROOT", source)
    kit.verify_source_snapshot([(document, "guide.md")], head)
    with pytest.raises(ValueError, match="Checkout HEAD"):
        kit.verify_source_snapshot([(document, "guide.md")], "b" * 40)
    document.write_text("uncommitted change")
    with pytest.raises(ValueError, match="Source differs"):
        kit.verify_source_snapshot([(document, "guide.md")], head)


def test_kit_includes_typescript_declarations_and_powershell_examples(
    fixture, tmp_path: Path
) -> None:
    source, artifacts = fixture
    for relative in (
        "examples/sdk/typescript/declarations-smoke.mts",
        "examples/sdk/powershell/quickstart.ps1",
    ):
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic integration example")
    output = tmp_path / "kit"
    kit.build_kit(artifacts, output, commit=COMMIT)
    assert (output / "examples/sdk/typescript/declarations-smoke.mts").exists()
    assert (output / "examples/sdk/powershell/quickstart.ps1").exists()
    readme = (output / "README.md").read_text()
    assert "PowerShell 7 REST/CLI integration examples" in readme
    assert "not a native PowerShell SDK" in readme
    kit.verify_kit(output, commit=COMMIT)
