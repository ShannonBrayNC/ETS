#!/usr/bin/env python3
"""Fail-closed static dependency sweep for the LanternProtocol.net deployable site."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_SCHEMA = "ets.lantern.content-dependency-sweep.v1"
_TEXT_SUFFIXES = {".html", ".js", ".css", ".svg", ".json", ".xml", ".txt"}
_URL_PATTERN = re.compile(r"https?://[^\s\"'<>)}]+", re.IGNORECASE)
_FORBIDDEN_LITERALS = {
    "38ac7b7f-65e1-4a2a-8e3a-7bbe18659ebe": "source_tenant_id",
    "a352eb89-ae3a-46c8-a08f-308138307a6f": "source_subscription_id",
    "rg-ets-live-eastus": "source_resource_group",
    "etsq1a352eb89": "source_acr",
    "etsgwo23bf2d6oq44s": "source_gateway_storage",
    "lanternbkpd1283bda7c363": "source_lantern_storage",
    "lantern-azure-d1283bda7c363-hjb5gze4a4esbjb7.z03.azurefd.net": "source_frontdoor_host",
}
_FORBIDDEN_HOST_SUFFIXES = (
    ".azurefd.net",
    ".web.core.windows.net",
    ".blob.core.windows.net",
    ".file.core.windows.net",
    ".azurecontainerapps.io",
    ".vault.azure.net",
)
# W3C namespace identifiers use HTTP-shaped URIs but are not network dependencies.
_NON_NETWORK_NAMESPACE_URIS = {
    "http://www.w3.org/2000/svg",
    "http://www.w3.org/1999/xlink",
    "http://www.w3.org/1999/xhtml",
    "http://www.w3.org/2001/xmlschema",
    "http://www.w3.org/2001/xmlschema-instance",
}


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


def _text_files(root: Path) -> list[Path]:
    if not root.is_dir():
        raise ValueError("Lantern site root is missing")
    files = [
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.casefold() in _TEXT_SUFFIXES
    ]
    if not files:
        raise ValueError("Lantern site root contains no text assets")
    return sorted(files)


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def sweep(root: Path) -> dict[str, Any]:
    files = _text_files(root)
    blockers: list[dict[str, str]] = []
    urls: set[str] = set()
    hosts: set[str] = set()
    namespace_uris: set[str] = set()
    insecure_external: list[dict[str, str]] = []
    robots_values: list[str] = []

    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"Lantern text asset is not UTF-8: {_relative(path, root)}") from exc
        lowered = text.casefold()
        relative = _relative(path, root)

        for literal, category in _FORBIDDEN_LITERALS.items():
            if literal.casefold() in lowered:
                blockers.append({"file": relative, "category": category, "value": literal})

        for raw_url in _URL_PATTERN.findall(text):
            cleaned = raw_url.rstrip(".,;:")
            if cleaned.casefold() in _NON_NETWORK_NAMESPACE_URIS:
                namespace_uris.add(cleaned)
                continue
            urls.add(cleaned)
            parsed = urlparse(cleaned)
            host = (parsed.hostname or "").casefold()
            if host:
                hosts.add(host)
                if any(host.endswith(suffix) for suffix in _FORBIDDEN_HOST_SUFFIXES):
                    blockers.append(
                        {"file": relative, "category": "direct_azure_provider_endpoint", "value": host}
                    )
                if parsed.scheme.casefold() == "http" and host not in {"localhost", "127.0.0.1"}:
                    insecure_external.append({"file": relative, "url": cleaned})

        if path.suffix.casefold() == ".html":
            for match in re.finditer(
                r'<meta\s+[^>]*name=["\']robots["\'][^>]*content=["\']([^"\']+)["\']',
                text,
                flags=re.IGNORECASE,
            ):
                robots_values.append(match.group(1).strip().casefold())

    if insecure_external:
        blockers.extend(
            {
                "file": item["file"],
                "category": "insecure_external_url",
                "value": item["url"],
            }
            for item in insecure_external
        )

    robots_noindex = any("noindex" in value for value in robots_values)
    return {
        "schema_version": _SCHEMA,
        "claim": "static_lantern_source_dependency_sweep",
        "site_root": root.as_posix(),
        "files_scanned": len(files),
        "external_hosts": sorted(hosts),
        "external_urls": sorted(urls),
        "non_network_namespace_uris": sorted(namespace_uris),
        "blockers": sorted(
            blockers,
            key=lambda item: (item["file"], item["category"], item["value"]),
        ),
        "source_dependency_free": not blockers,
        "robots_meta_values": sorted(set(robots_values)),
        "search_index_ready": not robots_noindex,
        "cutover_note": (
            "Remove continuity noindex/nofollow before or during production cutover "
            "if public search indexing is intended."
            if robots_noindex
            else "No noindex robots directive detected."
        ),
    }


def _write_summary(report: dict[str, Any]) -> None:
    lines = [
        "## LanternProtocol.net static dependency sweep",
        "",
        f"- files scanned: `{report['files_scanned']}`",
        f"- source dependency free: `{str(report['source_dependency_free']).lower()}`",
        f"- blocking references: `{len(report['blockers'])}`",
        f"- external hosts discovered: `{len(report['external_hosts'])}`",
        f"- non-network namespace URIs: `{len(report['non_network_namespace_uris'])}`",
        f"- search-index ready: `{str(report['search_index_ready']).lower()}`",
        f"- cutover note: {report['cutover_note']}",
    ]
    if report["external_hosts"]:
        lines.extend(["", "External hosts observed:"])
        lines.extend(f"- `{host}`" for host in report["external_hosts"])
    if report["blockers"]:
        lines.extend(["", "Blocking source/provider references:"])
        for item in report["blockers"]:
            lines.append(
                f"- `{item['file']}` — `{item['category']}` — `{item['value']}`"
            )
    content = "\n".join(lines) + "\n"
    print(content, end="")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-root", default="ops/lantern-site-backup/site")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        report = sweep(Path(args.site_root))
        _write_private_json(Path(args.output), report)
        _write_summary(report)
    except (OSError, ValueError) as exc:
        print(f"Lantern static dependency sweep blocked: {type(exc).__name__}")
        return 2
    return 0 if report["source_dependency_free"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
