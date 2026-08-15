#!/usr/bin/env python3
"""Fail-closed verification and extraction for pinned IPQ A-F GitHub artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

_API_VERSION = "2026-03-10"
_REPOSITORY = "ShannonBrayNC/ETS"
_REQUIRED_FAMILIES = frozenset("ABCDEF")
_REDIRECT_CODES = frozenset({301, 302, 303, 307, 308})


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(  # type: ignore[override]
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


def _api_request(url: str, token: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": _API_VERSION,
            "User-Agent": "ets-ipq-g-artifact-verifier",
        },
    )


def _fetch_json(url: str, token: str) -> dict[str, Any]:
    with urllib.request.urlopen(_api_request(url, token), timeout=30) as response:
        return json.load(response)


def _artifact_download_location(artifact_id: int, token: str) -> str:
    url = f"https://api.github.com/repos/{_REPOSITORY}/actions/artifacts/{artifact_id}/zip"
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        opener.open(_api_request(url, token), timeout=30)
    except urllib.error.HTTPError as exc:
        if exc.code not in _REDIRECT_CODES:
            raise
        location = exc.headers.get("Location")
        if not location:
            raise RuntimeError(f"artifact {artifact_id} download redirect had no Location") from exc
        return location
    raise RuntimeError(f"artifact {artifact_id} download did not return an expected redirect")


def _download_and_hash(url: str, destination: Path) -> str:
    digest = hashlib.sha256()
    request = urllib.request.Request(url, headers={"User-Agent": "ets-ipq-g-artifact-verifier"})
    with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            digest.update(chunk)
            output.write(chunk)
    return f"sha256:{digest.hexdigest()}"


def _safe_extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            member_path = PurePosixPath(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError(f"unsafe artifact path: {member.filename}")
            unix_mode = member.external_attr >> 16
            if unix_mode & 0o170000 == 0o120000:
                raise ValueError(f"artifact contains a symbolic link: {member.filename}")
            resolved = (destination / Path(*member_path.parts)).resolve()
            if destination.resolve() not in resolved.parents and resolved != destination.resolve():
                raise ValueError(f"artifact extraction escaped destination: {member.filename}")
        bundle.extractall(destination)


def _validate_manifest(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if payload.get("schema_version") != "ets.ipq_g.retained_artifacts.v1":
        raise ValueError("unsupported retained-artifact manifest schema")
    frozen_sha = payload.get("frozen_sut_sha")
    if frozen_sha != os.environ.get("IPQ_FROZEN_SUT_SHA"):
        raise ValueError("manifest frozen SUT SHA does not match workflow authority")
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("retained-artifact manifest has no artifacts")

    families: set[str] = set()
    ids: set[int] = set()
    for item in artifacts:
        if not isinstance(item, dict):
            raise ValueError("retained-artifact entry is not an object")
        family = item.get("family")
        artifact_id = item.get("id")
        digest = item.get("digest")
        if family not in _REQUIRED_FAMILIES:
            raise ValueError(f"unexpected IPQ family: {family}")
        if not isinstance(artifact_id, int) or artifact_id <= 0 or artifact_id in ids:
            raise ValueError(f"invalid or duplicate artifact id: {artifact_id}")
        if not isinstance(digest, str) or not digest.startswith("sha256:") or len(digest) != 71:
            raise ValueError(f"invalid digest for artifact {artifact_id}")
        families.add(family)
        ids.add(artifact_id)

    if families != _REQUIRED_FAMILIES:
        raise ValueError(f"manifest families must be A-F exactly; got {sorted(families)}")
    return artifacts


def _verify_metadata(expected: dict[str, Any], actual: dict[str, Any]) -> None:
    artifact_id = expected["id"]
    checks = {
        "id": actual.get("id"),
        "name": actual.get("name"),
        "digest": actual.get("digest"),
    }
    for key, actual_value in checks.items():
        if actual_value != expected[key]:
            raise ValueError(
                f"artifact {artifact_id} metadata mismatch for {key}: "
                f"expected={expected[key]!r} actual={actual_value!r}"
            )
    if actual.get("expired") is not False:
        raise ValueError(f"artifact {artifact_id} is expired or has unknown expiry state")
    workflow_run = actual.get("workflow_run")
    if not isinstance(workflow_run, dict):
        raise ValueError(f"artifact {artifact_id} has no workflow_run metadata")
    if workflow_run.get("id") != expected["run_id"]:
        raise ValueError(f"artifact {artifact_id} workflow run id mismatch")
    if workflow_run.get("head_sha") != expected["head_sha"]:
        raise ValueError(f"artifact {artifact_id} workflow head SHA mismatch")


def verify_and_extract(manifest: Path, output_root: Path, token: str) -> dict[str, Any]:
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    artifacts = _validate_manifest(payload)
    output_root.mkdir(parents=True, exist_ok=True)
    verified: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="ets-ipq-g-") as temp_dir:
        temporary = Path(temp_dir)
        for expected in artifacts:
            artifact_id = expected["id"]
            metadata_url = (
                f"https://api.github.com/repos/{_REPOSITORY}/actions/artifacts/{artifact_id}"
            )
            metadata = _fetch_json(metadata_url, token)
            _verify_metadata(expected, metadata)

            archive = temporary / f"{artifact_id}.zip"
            location = _artifact_download_location(artifact_id, token)
            downloaded_digest = _download_and_hash(location, archive)
            if downloaded_digest != expected["digest"]:
                raise ValueError(
                    f"artifact {artifact_id} ZIP digest mismatch: "
                    f"expected={expected['digest']} actual={downloaded_digest}"
                )

            destination = output_root / expected["family"].lower() / expected["name"]
            if destination.exists():
                shutil.rmtree(destination)
            _safe_extract(archive, destination)
            verified.append(
                {
                    "family": expected["family"],
                    "id": artifact_id,
                    "name": expected["name"],
                    "run_id": expected["run_id"],
                    "head_sha": expected["head_sha"],
                    "digest": downloaded_digest,
                    "extracted_to": str(destination.relative_to(output_root)),
                }
            )

    result = {
        "schema_version": "ets.ipq_g.verified_artifacts.v1",
        "frozen_sut_sha": payload["frozen_sut_sha"],
        "artifact_count": len(verified),
        "verified_artifacts": verified,
        "result": "PASS",
    }
    (output_root.parent / "verified-artifacts.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    source_runs: dict[str, set[int]] = {}
    for item in verified:
        source_runs.setdefault(item["family"], set()).add(item["run_id"])
    (output_root.parent / "source-runs.txt").write_text(
        "".join(
            f"{family}={','.join(str(run_id) for run_id in sorted(source_runs[family]))}\n"
            for family in sorted(source_runs)
        ),
        encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output_root", type=Path)
    args = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required")
    result = verify_and_extract(args.manifest, args.output_root, token)
    print(f"verified retained IPQ artifact ZIPs={result['artifact_count']}")


if __name__ == "__main__":
    main()
