"""Assemble/verify an integrity-recorded SDK test kit, never publish a release."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "test-kit-manifest.json"
SKIP = frozenset({"__pycache__", "node_modules", "bin", "obj", ".git", ".venv"})
SOURCE_DIRS = (
    "docs/sdk",
    "docs/commercial",
    "examples/sdk",
    "conformance/sdk",
    "tests/fixtures/verifier",
)
SOURCE_FILES = (
    "LICENSE",
    "NOTICE",
    "docs/security/CORE_API_AUTHORIZATION.md",
    "scripts/build_sdk_test_kit.py",
)
SOURCE_EXTENSIONS = frozenset(
    {".md", ".json", ".py", ".cs", ".csproj", ".mjs", ".ts", ".mts", ".ps1"}
)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def read_json(path: Path) -> Any:
    with path.open("rb") as stream:
        value = stream.read(4 * 1024 * 1024 + 1)
    if len(value) > 4 * 1024 * 1024:
        raise ValueError("Manifest exceeds 4 MiB")
    return json.loads(value, object_pairs_hook=pairs)


def relative_path(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError("Unsafe relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
        raise ValueError("Unsafe relative path")
    if any(ord(char) < 32 for char in value):
        raise ValueError("Unsafe relative path")
    return value


def regular_file(root: Path, relative: str) -> Path:
    path = root
    for part in PurePosixPath(relative).parts:
        path = path / part
        info = path.lstat()
        mode = info.st_mode
        if stat.S_ISLNK(mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("Symlinks are not permitted")
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError("Expected regular file")
    return path


def directory(path: Path) -> None:
    info = path.lstat()
    mode = info.st_mode
    if (
        not stat.S_ISDIR(mode)
        or stat.S_ISLNK(mode)
        or getattr(info, "st_file_attributes", 0) & 0x400
    ):
        raise ValueError("Expected non-symlink directory")


def files_under(root: Path, *, exclude_generated: bool = False) -> list[str]:
    directory(root)
    result: list[str] = []
    for folder, folders, files in os.walk(root, followlinks=False):
        if exclude_generated:
            folders[:] = [name for name in folders if name not in SKIP]
        for name in folders:
            directory(Path(folder) / name)
        for name in files:
            relative = (Path(folder) / name).relative_to(root).as_posix()
            regular_file(root, relative)
            result.append(relative)
    return sorted(result)


def validate_entries(root: Path, entries: Any) -> list[dict[str, Any]]:
    if not isinstance(entries, list) or not entries:
        raise ValueError("Empty or invalid file manifest")
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in entries:
        if not isinstance(item, dict):
            raise ValueError("Invalid file entry")
        name = relative_path(item.get("path"))
        if name.casefold() in seen:
            raise ValueError("Duplicate or case-colliding file path")
        seen.add(name.casefold())
        size = item.get("size_bytes")
        expected = item.get("sha256")
        if type(size) is not int or size < 0:
            raise ValueError("Invalid file size")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("Invalid SHA-256")
        path = regular_file(root, name)
        if path.stat().st_size != size or digest(path) != expected:
            raise ValueError(f"Artifact hash/size mismatch: {name}")
        result.append(item)
    return result


def validate_artifacts(artifacts: Path, commit: str) -> dict[str, Any]:
    directory(artifacts)
    manifest_path = regular_file(artifacts, "sdk-release-manifest.json")
    manifest = read_json(manifest_path)
    matrix = read_json(ROOT / "docs/sdk/RELEASE_MATRIX.json")
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != "ets.sdk.release_manifest.v1"
    ):
        raise ValueError("Invalid SDK release manifest")
    if manifest.get("source_commit") != commit:
        raise ValueError("SDK artifact source commit does not match requested kit commit")
    for field in ("release_tag", "sdk_contract", "packages"):
        if manifest.get(field) != matrix[field]:
            raise ValueError(f"SDK release matrix mismatch: {field}")
    entries = validate_entries(artifacts, manifest.get("artifacts"))
    paths = {entry["path"] for entry in entries}
    required = {
        "Python wheel": ("python/", ".whl"),
        "Python sdist": ("python/", ".tar.gz"),
        ".NET package": ("dotnet/", ".nupkg"),
        ".NET symbols": ("dotnet/", ".snupkg"),
        "npm package": ("typescript/", ".tgz"),
    }
    for label, (prefix, suffix) in required.items():
        if not any(name.startswith(prefix) and name.endswith(suffix) for name in paths):
            raise ValueError(f"Missing {label}")
    if "sdk-release.spdx.json" not in paths:
        raise ValueError("Missing SDK SPDX SBOM")
    known = paths | {"sdk-release-manifest.json", "SHA256SUMS"}
    if set(files_under(artifacts)) != known:
        raise ValueError("Unexpected or missing SDK artifact file")
    sums = regular_file(artifacts, "SHA256SUMS").read_text(encoding="utf-8")
    expected_sums = "".join(f"{item['sha256']}  {item['path']}\n" for item in entries)
    if sums != expected_sums:
        raise ValueError("SHA256SUMS does not match SDK manifest")
    return manifest


def rewrite_source_links(output: Path, relative: str, commit: str) -> None:
    """Keep bundled relative links; point omitted source references at exact Git source."""
    path = output / relative
    repository = ROOT.resolve()

    def replace(match: re.Match[str]) -> str:
        target = match.group(1)
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or not parsed.path or target.startswith("#"):
            return match.group(0)
        decoded = unquote(parsed.path)
        source = (ROOT / relative).parent.joinpath(decoded).resolve()
        if not source.is_relative_to(repository):
            raise ValueError("Markdown link escapes repository")
        repo_path = source.relative_to(repository).as_posix()
        if (output / repo_path).exists():
            return match.group(0)
        destination = f"https://github.com/ShannonBrayNC/ETS/blob/{commit}/{quote(repo_path)}"
        if parsed.query:
            destination += "?" + parsed.query
        if parsed.fragment:
            destination += "#" + parsed.fragment
        return "](" + destination + ")"

    text = path.read_text(encoding="utf-8")
    path.write_text(re.sub(r"\]\(([^)]+)\)", replace, text), encoding="utf-8")


def verify_kit(output: Path, *, commit: str | None = None) -> dict[str, Any]:
    directory(output)
    data = read_json(regular_file(output, MANIFEST))
    if not isinstance(data, dict) or data.get("schema_version") != "ets.sdk.test_kit.v1":
        raise ValueError("Invalid test-kit manifest")
    source = data.get("source_commit")
    if not isinstance(source, str) or not re.fullmatch(r"[0-9a-f]{40}", source):
        raise ValueError("Invalid source commit")
    if commit is not None and source != commit:
        raise ValueError("Test-kit source commit mismatch")
    if data.get("distribution_scope") != "alpha-testing-only":
        raise ValueError("Invalid distribution scope")
    entries = validate_entries(output, data.get("files"))
    if {entry["path"] for entry in entries} | {MANIFEST} != set(files_under(output)):
        raise ValueError("Unexpected or missing test-kit file")
    validate_artifacts(output / "packages", source)
    return data


def verify_source_snapshot(sources: list[tuple[Path, str]], commit: str) -> None:
    """Bind copied guides/examples to the same Git snapshot as the package artifacts."""
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    if head != commit:
        raise ValueError("Checkout HEAD does not match SDK artifact source commit")
    for source, relative in sources:
        if relative.startswith("packages/"):
            continue
        original = subprocess.run(
            ["git", "show", f"{commit}:{relative}"], cwd=ROOT, check=True, capture_output=True
        ).stdout
        if hashlib.sha256(original).hexdigest() != digest(source):
            raise ValueError(f"Source differs from declared commit: {relative}")


def build_kit(artifacts: Path, output: Path, *, commit: str) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Commit must be exactly 40 lowercase hexadecimal characters")
    if os.path.lexists(output):
        raise FileExistsError("Use a new output directory")
    manifest = validate_artifacts(artifacts, commit)
    sources: list[tuple[Path, str]] = []
    for folder in SOURCE_DIRS:
        for name in files_under(ROOT / folder, exclude_generated=True):
            if Path(name).suffix in SOURCE_EXTENSIONS:
                sources.append((regular_file(ROOT / folder, name), f"{folder}/{name}"))
    for name in SOURCE_FILES:
        sources.append((regular_file(ROOT, name), name))
    for name in files_under(artifacts):
        sources.append((regular_file(artifacts, name), f"packages/{name}"))
    verify_source_snapshot(sources, commit)
    output.mkdir(parents=False, exist_ok=False)
    for source, relative in sources:
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for _, relative in sources:
        if relative.endswith(".md") and not relative.startswith("packages/"):
            rewrite_source_links(output, relative, commit)
    readme = f"""# ETS SDK alpha test kit

Source commit: `{commit}`

SDK contract: `{manifest["sdk_contract"]}`

SDK release line: `{manifest["release_tag"]}`

Start with [installation and test checklist](docs/sdk/TEST_KIT.md), then the
[task/API reference](docs/sdk/TASK_GUIDE.md) and [industry recipes](docs/sdk/INDUSTRY_COOKBOOK.md).
Actual package files are under `packages/python`, `packages/dotnet` and `packages/typescript`.

This is a synthetic test package, not a production deployment, registry publication,
Store submission or the planned Developer Edition authoring UI. No private key is
included; public deterministic smoke identities must never be trusted for real evidence.
Python 3.12+, .NET 8 SDK and Node 22.14+ are external developer prerequisites.
PowerShell 7 REST/CLI integration examples are included; they are not a native PowerShell SDK.
Dependency restore may require network; this kit is not an offline toolchain/wheelhouse.
The existing Windows desktop verifier remains a separately signed/qualified product.

`test-kit-manifest.json` records exact sizes/SHA-256 for all files except itself.
Compare the delivered outer archive hash through the trusted handoff. These unsigned
hash records detect changes; they do not establish authorship or release approval.
The SDK manifest records a PR merge commit when built in PR CI; it need not equal
its branch head. Installed-consumer CI results are separate acceptance evidence.

Bundled guides/samples work offline after dependency/toolchain preparation. Source-reference
links to omitted implementation/tests use this immutable snapshot and require internet:
https://github.com/ShannonBrayNC/ETS/tree/{commit}

Verification from the extracted kit root (standard-library Python only):
`python scripts/build_sdk_test_kit.py --verify . --commit-sha {commit}`

LICENSE and NOTICE plus package-specific notices remain applicable. Do not add
customer data, tokens, signing secrets or real regulated records to these examples.
"""
    (output / "README.md").write_text(readme, encoding="utf-8")
    entries = [
        {
            "path": name,
            "size_bytes": (output / name).stat().st_size,
            "sha256": digest(output / name),
        }
        for name in files_under(output)
    ]
    data = {
        "schema_version": "ets.sdk.test_kit.v1",
        "source_commit": commit,
        "distribution_scope": "alpha-testing-only",
        "sdk_contract": manifest["sdk_contract"],
        "files": entries,
    }
    (output / MANIFEST).write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return verify_kit(output, commit=commit)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--commit-sha")
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify:
        if args.artifacts or args.output:
            parser.error("--verify cannot be combined with --artifacts/--output")
        result = verify_kit(args.verify, commit=args.commit_sha)
    else:
        if not args.artifacts or not args.output or not args.commit_sha:
            parser.error("Building requires --artifacts, --output and --commit-sha")
        result = build_kit(args.artifacts, args.output, commit=args.commit_sha)
    print(f"Verified SDK test kit: {result['source_commit']} / {len(result['files'])} files")


if __name__ == "__main__":
    main()
