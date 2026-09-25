"""Fail-closed validation for the ETS SDK public-release compatibility matrix."""

from __future__ import annotations

import json
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

from ets.sdk import APPLICATION_SDK_COMPATIBILITY_V1

ROOT = Path(__file__).resolve().parents[1]


def _require_text(element: ET.Element | None, name: str) -> str:
    if element is None or element.text is None or not element.text.strip():
        raise RuntimeError(f"NuGet project is missing {name}")
    return element.text.strip()


def main() -> None:
    matrix = json.loads((ROOT / "docs/sdk/RELEASE_MATRIX.json").read_text(encoding="utf-8"))
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    npm = json.loads((ROOT / "sdk/typescript/package.json").read_text(encoding="utf-8"))
    dotnet_root = ET.parse(
        ROOT / "sdk/dotnet/Ets.Application/Ets.Application.csproj"
    ).getroot()

    python_package = matrix["packages"]["python"]
    dotnet_package = matrix["packages"]["dotnet"]
    typescript_package = matrix["packages"]["typescript"]

    project = pyproject["project"]
    if project["name"] != python_package["distribution"]:
        raise RuntimeError("Python distribution name does not match SDK release matrix")
    if project["version"] != python_package["version"]:
        raise RuntimeError("Python package version does not match SDK release matrix")
    if project["name"] == "ets":
        raise RuntimeError("Python distribution name 'ets' is reserved by an unrelated project")

    if npm["name"] != typescript_package["package_name"]:
        raise RuntimeError("npm package name does not match SDK release matrix")
    if npm["version"] != typescript_package["version"]:
        raise RuntimeError("npm package version does not match SDK release matrix")
    if npm.get("private") is not False:
        raise RuntimeError("npm public-release package must set private=false")

    package_id = _require_text(dotnet_root.find(".//PackageId"), "PackageId")
    package_version = _require_text(dotnet_root.find(".//Version"), "Version")
    target_framework = _require_text(dotnet_root.find(".//TargetFramework"), "TargetFramework")
    if package_id != dotnet_package["package_id"]:
        raise RuntimeError("NuGet package ID does not match SDK release matrix")
    if package_version != dotnet_package["version"]:
        raise RuntimeError("NuGet package version does not match SDK release matrix")
    if target_framework != dotnet_package["target_framework"]:
        raise RuntimeError("NuGet target framework does not match SDK release matrix")

    if matrix["sdk_contract"] != APPLICATION_SDK_COMPATIBILITY_V1.sdk_contract:
        raise RuntimeError("SDK contract does not match Python compatibility declaration")
    if matrix["api_versions"] != list(APPLICATION_SDK_COMPATIBILITY_V1.api_versions):
        raise RuntimeError("API versions do not match Python compatibility declaration")

    print(
        "ETS SDK release matrix verified: "
        f"{matrix['release_tag']} / {matrix['sdk_contract']}"
    )


if __name__ == "__main__":
    main()
