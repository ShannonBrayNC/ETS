"""Build a deterministic SHA-256 manifest for ETS SDK release artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_EXCLUDED = frozenset({"SHA256SUMS", "sdk-release-manifest.json"})


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(artifacts_dir: Path, *, source_commit: str) -> dict[str, object]:
    matrix = json.loads((ROOT / "docs/sdk/RELEASE_MATRIX.json").read_text(encoding="utf-8"))
    files: list[dict[str, object]] = []
    for path in sorted(item for item in artifacts_dir.rglob("*") if item.is_file()):
        if path.name in _EXCLUDED:
            continue
        relative = path.relative_to(artifacts_dir).as_posix()
        files.append(
            {
                "path": relative,
                "sha256": _sha256(path),
                "size_bytes": path.stat().st_size,
            }
        )

    if not files:
        raise RuntimeError("no SDK release artifacts were found")

    return {
        "schema_version": "ets.sdk.release_manifest.v1",
        "release_tag": matrix["release_tag"],
        "sdk_contract": matrix["sdk_contract"],
        "source_commit": source_commit,
        "packages": matrix["packages"],
        "artifacts": files,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", default="artifacts")
    parser.add_argument("--output", default="artifacts/sdk-release-manifest.json")
    parser.add_argument("--checksums", default="artifacts/SHA256SUMS")
    parser.add_argument("--commit-sha", default=os.getenv("GITHUB_SHA", "unknown"))
    args = parser.parse_args()

    artifacts_dir = (ROOT / args.artifacts).resolve()
    output_path = (ROOT / args.output).resolve()
    checksum_path = (ROOT / args.checksums).resolve()
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    manifest = build_manifest(artifacts_dir, source_commit=args.commit_sha)
    output_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        f"{item['sha256']}  {item['path']}"
        for item in manifest["artifacts"]
        if isinstance(item, dict)
    ]
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"wrote {output_path}")
    print(f"wrote {checksum_path}")


if __name__ == "__main__":
    main()
