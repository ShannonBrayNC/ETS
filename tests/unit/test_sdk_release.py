import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_sdk_release_matrix_matches_package_metadata() -> None:
    subprocess.run(
        [sys.executable, "scripts/verify_sdk_release_matrix.py"],
        cwd=ROOT,
        check=True,
    )


def test_sdk_release_manifest_hashes_artifacts(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    (artifacts / "python").mkdir(parents=True)
    (artifacts / "dotnet").mkdir()
    first = artifacts / "python" / "sample.whl"
    second = artifacts / "dotnet" / "sample.nupkg"
    first.write_bytes(b"python-sdk")
    second.write_bytes(b"dotnet-sdk")

    output = artifacts / "sdk-release-manifest.json"
    checksums = artifacts / "SHA256SUMS"
    subprocess.run(
        [
            sys.executable,
            "scripts/build_sdk_release_manifest.py",
            "--artifacts",
            str(artifacts),
            "--output",
            str(output),
            "--checksums",
            str(checksums),
            "--commit-sha",
            "a" * 40,
        ],
        cwd=ROOT,
        check=True,
    )

    manifest = json.loads(output.read_text(encoding="utf-8"))
    entries = {item["path"]: item["sha256"] for item in manifest["artifacts"]}
    assert entries["python/sample.whl"] == hashlib.sha256(b"python-sdk").hexdigest()
    assert entries["dotnet/sample.nupkg"] == hashlib.sha256(b"dotnet-sdk").hexdigest()
    assert manifest["source_commit"] == "a" * 40
    assert manifest["sdk_contract"] == "ets.application.sdk.v1"
    assert "sdk-release-manifest.json" not in entries
    assert "SHA256SUMS" not in entries


def test_public_publish_is_release_only_and_environment_protected() -> None:
    text = (ROOT / ".github/workflows/sdk-publish.yml").read_text(encoding="utf-8")
    assert "types: [published]" in text
    assert "environment: sdk-public-release" in text
    assert "id-token: write" in text
    assert "pypa/gh-action-pypi-publish@release/v1" in text
    assert "NuGet/login@v1" in text
    assert "npm publish" in text
    assert '"docs/sdk/RELEASE_MATRIX.json"' in text
    assert '"release_tag"' in text
    assert 'git rev-parse origin/main' in text
