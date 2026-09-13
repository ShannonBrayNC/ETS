#!/usr/bin/env python3
"""Verify destination Lantern static hosting and Front Door byte equivalence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

_SCHEMA = "ets.lantern.destination-staging.v1"


class StagingVerificationError(RuntimeError):
    """Raised when destination staging does not exactly serve the checked-in site."""


def _write_private_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        stat.S_IRUSR | stat.S_IWUSR,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, sort_keys=True, indent=2)
        stream.write("\n")


def _normalize_endpoint(value: str, kind: str) -> str:
    parsed = urllib.parse.urlsplit(value.strip())
    if parsed.scheme != "https" or not parsed.hostname or parsed.query or parsed.fragment:
        raise StagingVerificationError(f"{kind} endpoint must be a plain HTTPS origin")
    host = parsed.hostname.casefold()
    if kind == "storage":
        if not host.endswith(".web.core.windows.net"):
            raise StagingVerificationError("storage endpoint is not an Azure static website host")
    elif kind == "frontdoor":
        if not host.endswith(".azurefd.net"):
            raise StagingVerificationError("Front Door endpoint is not an Azure default host")
    else:
        raise StagingVerificationError("endpoint kind is invalid")
    path = parsed.path or "/"
    if path != "/":
        raise StagingVerificationError(f"{kind} endpoint must not include a path")
    return f"https://{parsed.hostname}/"


def _site_manifest(root: Path) -> tuple[list[dict[str, Any]], str, int]:
    if not root.is_dir():
        raise StagingVerificationError("Lantern site directory is unavailable")
    index = root / "index.html"
    if not index.is_file():
        raise StagingVerificationError("Lantern index.html is unavailable")
    index_text = index.read_text(encoding="utf-8")
    folded = index_text.casefold().replace(" ", "")
    if 'name="robots"' not in index_text.casefold() or "noindex,nofollow" not in folded:
        raise StagingVerificationError("staging site must preserve noindex, nofollow")

    files: list[dict[str, Any]] = []
    total_bytes = 0
    aggregate = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        total_bytes += len(data)
        files.append({"path": relative, "size": len(data), "sha256": digest})
        aggregate.update(relative.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(str(len(data)).encode("ascii"))
        aggregate.update(b"\0")
        aggregate.update(bytes.fromhex(digest))
    if not files:
        raise StagingVerificationError("Lantern site contains no deployable files")
    return files, aggregate.hexdigest(), total_bytes


def _fetch_bytes(url: str, timeout: float = 15.0) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "Accept-Encoding": "identity",
            "Cache-Control": "no-cache",
            "User-Agent": "lantern-destination-staging-verifier/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise StagingVerificationError(f"unexpected HTTP status {response.status}")
            return response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise StagingVerificationError("destination endpoint could not be read") from exc


def _verify_endpoint(
    base: str,
    manifest: list[dict[str, Any]],
) -> None:
    for item in manifest:
        relative = str(item["path"])
        encoded = urllib.parse.quote(relative, safe="/")
        data = _fetch_bytes(urllib.parse.urljoin(base, encoded))
        if len(data) != int(item["size"]):
            raise StagingVerificationError(f"destination byte length differs for {relative}")
        if hashlib.sha256(data).hexdigest() != str(item["sha256"]):
            raise StagingVerificationError(f"destination SHA-256 differs for {relative}")


def verify(
    *,
    site_root: Path,
    storage_endpoint: str,
    frontdoor_endpoint: str,
    storage_account: str,
    frontdoor_profile: str,
    frontdoor_endpoint_name: str,
    attempts: int = 1,
    delay_seconds: float = 0.0,
) -> dict[str, Any]:
    """Require every static file to match through destination Storage and Front Door."""
    if not 1 <= attempts <= 60:
        raise StagingVerificationError("attempt count is outside the allowed bound")
    if delay_seconds < 0 or delay_seconds > 60:
        raise StagingVerificationError("retry delay is outside the allowed bound")
    storage = _normalize_endpoint(storage_endpoint, "storage")
    frontdoor = _normalize_endpoint(frontdoor_endpoint, "frontdoor")
    manifest, aggregate_digest, total_bytes = _site_manifest(site_root)

    last_error: StagingVerificationError | None = None
    for attempt in range(attempts):
        try:
            _verify_endpoint(storage, manifest)
            _verify_endpoint(frontdoor, manifest)
            last_error = None
            break
        except StagingVerificationError as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(delay_seconds)
    if last_error is not None:
        raise last_error

    return {
        "schema_version": _SCHEMA,
        "claim": "destination_lantern_storage_and_frontdoor_exact",
        "site_file_count": len(manifest),
        "site_total_bytes": total_bytes,
        "site_manifest_sha256": aggregate_digest,
        "storage_account": storage_account,
        "storage_endpoint_host": urllib.parse.urlsplit(storage).hostname,
        "frontdoor_profile": frontdoor_profile,
        "frontdoor_endpoint_name": frontdoor_endpoint_name,
        "frontdoor_endpoint_host": urllib.parse.urlsplit(frontdoor).hostname,
        "storage_byte_equivalence": True,
        "frontdoor_byte_equivalence": True,
        "robots_noindex_nofollow": True,
        "production_custom_domain_attached": False,
        "production_dns_changed": False,
        "source_azure_mutation_performed": False,
        "ets_application_mutation_performed": False,
        "tenant_exit_ready": False,
    }


def _write_summary(result: dict[str, Any]) -> None:
    lines = [
        "## Lantern destination staging qualification",
        "",
        f"- files verified: `{result['site_file_count']}`",
        f"- total bytes: `{result['site_total_bytes']}`",
        f"- content manifest SHA-256: `{result['site_manifest_sha256']}`",
        f"- destination storage: `{result['storage_account']}`",
        f"- destination Front Door profile: `{result['frontdoor_profile']}`",
        f"- Front Door default host: `{result['frontdoor_endpoint_host']}`",
        "- storage byte equivalence: `pass`",
        "- Front Door byte equivalence: `pass`",
        "- robots noindex/nofollow: `preserved`",
        "- production custom domain: `not attached`",
        "- production DNS: `unchanged`",
        "- source Azure mutation: `not performed`",
        "- ETS application mutation: `not performed`",
        "- tenant_exit_ready: `false`",
        "",
        "The destination-native Lantern origin and default Front Door endpoint are qualified. "
        "Production custom-domain/TLS/DNS cutover remains a separate Gate 8 action.",
    ]
    content = "\n".join(lines) + "\n"
    print(content, end="")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-root", required=True)
    parser.add_argument("--storage-endpoint", required=True)
    parser.add_argument("--frontdoor-endpoint", required=True)
    parser.add_argument("--storage-account", required=True)
    parser.add_argument("--frontdoor-profile", required=True)
    parser.add_argument("--frontdoor-endpoint-name", required=True)
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--delay-seconds", type=float, default=0.0)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        result = verify(
            site_root=Path(args.site_root),
            storage_endpoint=args.storage_endpoint,
            frontdoor_endpoint=args.frontdoor_endpoint,
            storage_account=args.storage_account,
            frontdoor_profile=args.frontdoor_profile,
            frontdoor_endpoint_name=args.frontdoor_endpoint_name,
            attempts=args.attempts,
            delay_seconds=args.delay_seconds,
        )
        _write_private_json(Path(args.output), result)
        _write_summary(result)
    except (StagingVerificationError, OSError, ValueError) as exc:
        print(f"Lantern destination staging verification blocked: {type(exc).__name__}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
