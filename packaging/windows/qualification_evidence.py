"""Reconcile supplied Windows evidence offline; never perform or approve qualification."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import runpy
import shutil
import stat
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote

# Reuse the existing strict JSON, path and unsigned-review schema checks.
_RECORD = runpy.run_path(str(Path(__file__).with_name("candidate_record.py")))
read_object = _RECORD["read_object"]
digest = _RECORD["digest"]
reject_link = _RECORD["reject_link"]
IDENTITIES = {"verifier": "ETSVerifier.Development", "developer": "ETSDeveloper.Development"}
FOUNDATION = "{http://schemas.microsoft.com/appx/manifest/foundation/windows10}"
GATES = (
    "developmentSignature",
    "cleanClient",
    "installedLifecycle",
    "offlineBehavior",
    "accessibility",
    "wack",
    "licenses",
    "productionIdentity",
    "ownerApproval",
    "storeCertification",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def check_msix(path: Path, layout: dict[str, Any], identity: str, *, signed: bool) -> str:
    """Check payload bytes/manifest, not Authenticode trust or MSIX installability."""
    with zipfile.ZipFile(path) as archive:
        entries: dict[str, zipfile.ZipInfo] = {}
        folded: set[str] = set()
        infos = archive.infolist()
        require(
            len(infos) < 10000 and sum(i.file_size for i in infos) < 1024**3,
            "Package exceeds evidence inspection limits",
        )
        for info in infos:
            name = unquote(info.filename)
            parsed = PurePosixPath(name)
            require(
                not info.is_dir()
                and str(parsed) == name
                and not parsed.is_absolute()
                and ".." not in parsed.parts
                and "\\" not in name
                and ":" not in name
                and "\x00" not in name
                and name.casefold() not in folded
                and not stat.S_ISLNK(info.external_attr >> 16),
                "Unsafe or duplicate MSIX member",
            )
            folded.add(name.casefold())
            entries[name] = info
        extras = {"AppxBlockMap.xml", "[Content_Types].xml"}
        if signed:
            extras.add("AppxSignature.p7x")
        require(
            set(entries) == set(layout) | extras and not set(layout) & extras,
            "Package member set does not match the reviewed payload/signature state",
        )
        for name, expected in layout.items():
            require(
                isinstance(expected, str) and re.fullmatch("[0-9a-f]{64}", expected) is not None,
                "Invalid payload hash",
            )
            actual = hashlib.sha256()
            with archive.open(entries[name]) as stream:
                while chunk := stream.read(1024 * 1024):
                    actual.update(chunk)
            require(actual.hexdigest() == expected, "Changed reviewed payload: " + name)
        if signed:
            require(entries["AppxSignature.p7x"].file_size > 0, "Empty signature attachment")
        require(
            "AppxManifest.xml" in entries and entries["AppxManifest.xml"].file_size <= 1048576,
            "Missing or oversized package manifest",
        )
        text = archive.read(entries["AppxManifest.xml"]).decode("utf-8-sig")
        require(
            "<!DOCTYPE" not in text.upper() and "<!ENTITY" not in text.upper(),
            "DTD/entity declarations are not allowed",
        )
        root = ET.fromstring(text)
        nodes = root.findall(FOUNDATION + "Identity")
        require(
            root.tag == FOUNDATION + "Package" and len(nodes) == 1, "Expected one package identity"
        )
        fields = nodes[0].attrib
        version = fields.get("Version", "")
        require(
            fields.get("Name") == identity
            and fields.get("Publisher") == "CN=" + identity
            and fields.get("ProcessorArchitecture") == "x64"
            and fields.get("ResourceId", "") == "",
            "Wrong package edition/publisher",
        )
        require(
            re.fullmatch(
                r"(0|[1-9][0-9]{0,4})\.(0|[1-9][0-9]{0,4})\."
                r"(0|[1-9][0-9]{0,4})\.0",
                version,
            )
            is not None
            and all(int(v) <= 65535 for v in version.split(".")),
            "Invalid package version",
        )
        return version


def assemble(
    review: Path,
    output: Path,
    *,
    edition: str,
    source_sha: str,
    run_url: str,
    signed_package: Path | None = None,
    signing_record: Path | None = None,
    client_preflight: Path | None = None,
    installed_package: Path | None = None,
    wack_xml: Path | None = None,
    wack_html: Path | None = None,
    _validate_only: bool = False,
) -> dict[str, Any]:
    require(edition in IDENTITIES, "Unknown development edition")
    require(not output.exists() and not output.is_symlink(), "Choose a fresh evidence directory")
    require(not output.resolve().is_relative_to(review.resolve()), "Output must be outside review")
    supplied = [
        p
        for p in (
            signed_package,
            signing_record,
            client_preflight,
            installed_package,
            wack_xml,
            wack_html,
        )
        if p is not None
    ]
    paths = _RECORD["files_under"](review) + supplied
    require(len(paths) <= 4096, "Too many evidence files")
    total = 0
    for path in paths:
        reject_link(path)
        size = path.stat().st_size
        require(path.is_file() and size <= 512 * 1024**2, "Oversized or non-file evidence")
        total += size
    require(total <= 1024**3, "Evidence exceeds aggregate byte limit")
    require(
        all(p is None or p.stat().st_size <= 64 * 1024**2 for p in (wack_xml, wack_html)),
        "WACK attachment exceeds byte limit",
    )
    # Pin the inputs before semantic validation, not after it.
    snapshot = {p.resolve(): {"sha256": digest(p), "bytes": p.stat().st_size} for p in paths}
    record = _RECORD["verify"](review)
    require(
        record["sourceSha"] == source_sha and record["workflowRun"] == run_url,
        "Review source/run does not match the independently selected candidate",
    )
    identity = IDENTITIES[edition]
    qualification = read_object(review / "package/qualification.json")
    layout = read_object(review / "package/layout-sha256.json")
    packages = [p for p in (review / "package").iterdir() if p.suffix.lower() == ".msix"]
    require(len(packages) == 1, "Expected one unsigned candidate package")
    unsigned = packages[0]
    unsigned_hash = digest(unsigned)
    version = check_msix(unsigned, layout, identity, signed=False)
    require(
        qualification.get("package") == unsigned.name
        and unsigned.name == f"{identity}_{version}_x64_unsigned.msix"
        and qualification.get("sha256") == unsigned_hash
        and qualification.get("identity") == identity
        and qualification.get("publisher") == "CN=" + identity
        and qualification.get("edition") == edition
        and qualification.get("version") == version
        and qualification.get("signed") is False
        and qualification.get("manifestValidated") is True
        and qualification.get("payloadHashesVerified") is True
        and all(
            qualification.get(k) is False
            for k in (
                "installationTested",
                "cleanWindows11Qualified",
                "wackPassed",
                "licensesApproved",
                "releaseApproved",
            )
        ),
        "Package qualification metadata does not match the reviewed package",
    )
    require(
        (signed_package is None) == (signing_record is None),
        "Supply signed package and signing record together",
    )
    require(
        signed_package is not None
        or not any((client_preflight, installed_package, wack_xml, wack_html)),
        "Client/WACK evidence needs the corresponding signed package and record",
    )
    inputs = {"review/candidate.json": review / "candidate.json"}
    inputs.update({"review/" + name: review / name for name in record["files"]})
    optional = {
        "signing/signing.json": signing_record,
        "client/client-preflight.json": client_preflight,
        "client/installed-package.json": installed_package,
        "wack/report.xml": wack_xml,
        "wack/report.html": wack_html,
    }
    if signed_package:
        inputs["signing/" + signed_package.name] = signed_package
    for name, path in optional.items():
        if path is not None:
            reject_link(path)
            require(path.is_file(), "Evidence must be a regular file")
            inputs[name] = path
    for path in inputs.values():
        reject_link(path)
        require(
            path.is_file() and not output.resolve().is_relative_to(path.resolve()),
            "Evidence must be a regular input file outside output",
        )
    signed_hash: str | None = None
    if signed_package is not None and signing_record is not None:
        signed_hash = digest(signed_package)
        signing = read_object(signing_record)
        require(
            check_msix(signed_package, layout, identity, signed=True) == version,
            "Signed package version differs",
        )
        require(
            signing.get("package") == signed_package.name
            and signed_package.name == f"{identity}_{version}_x64_signed.msix"
            and signing.get("sha256") == signed_hash
            and signing.get("unsignedSha256") == unsigned_hash
            and signing.get("reviewedUnsignedSha256") == unsigned_hash
            and signing.get("identity") == identity
            and signing.get("publisher") == "CN=" + identity
            and signing.get("edition") == edition
            and signing.get("architecture") == "x64"
            and signing.get("version") == version
            and signing.get("signed") is True
            and signing.get("signatureVerifiedOnSigningMachine") is True
            and isinstance(signing.get("certificateThumbprint"), str)
            and re.fullmatch("[0-9A-Fa-f]{40}", signing["certificateThumbprint"]) is not None,
            "Signing record does not match reviewed source/package/edition",
        )
        if client_preflight:
            client = read_object(client_preflight)
            require(
                type(client.get("schemaVersion")) is int
                and client["schemaVersion"] == 1
                and client.get("package") == signed_package.name
                and client.get("sha256") == signed_hash
                and client.get("expectedSha256") == signed_hash
                and (
                    client.get("signerThumbprint") is None
                    or (
                        isinstance(client["signerThumbprint"], str)
                        and client["signerThumbprint"].lower()
                        == signing["certificateThumbprint"].lower()
                    )
                )
                and client.get("clientQualified") is False
                and client.get("releaseApproved") is False,
                "Client preflight does not match the supplied signed candidate",
            )
        if installed_package:
            installed = read_object(installed_package)
            observed_version = installed.get("Version")
            if isinstance(observed_version, dict):
                values = [observed_version.get(k) for k in ("Major", "Minor", "Build", "Revision")]
                require(
                    all(type(v) is int and 0 <= v <= 65535 for v in values),
                    "Invalid observed installed version",
                )
                observed_version = ".".join(str(v) for v in values)
            architecture = installed.get("Architecture")
            require(
                installed.get("Name") == identity
                and installed.get("Publisher") == "CN=" + identity
                and observed_version == version
                and (
                    (isinstance(architecture, str) and architecture.lower() == "x64")
                    or (type(architecture) is int and architecture == 9)
                )
                and isinstance(installed.get("PackageFullName"), str)
                and re.fullmatch(
                    re.escape(f"{identity}_{version}_x64__") + r"[0-9a-hjkmnp-tv-z]{13}",
                    installed["PackageFullName"],
                )
                is not None,
                "Installed-package observation conflicts with the supplied candidate",
            )
    # Hash opaque WACK files but never parse success, run WACK, or assert package binding from XML.
    inventory = {name: snapshot[path.resolve()] for name, path in inputs.items()}
    require(
        all(
            digest(path) == inventory[name]["sha256"]
            and path.stat().st_size == inventory[name]["bytes"]
            for name, path in inputs.items()
        ),
        "Evidence changed during validation",
    )
    result = {
        "schemaVersion": 1,
        "recordType": "ets.windows.qualification-evidence",
        "sourceSha": source_sha,
        "workflowRun": run_url,
        "edition": edition,
        "identity": identity,
        "publisher": "CN=" + identity,
        "architecture": "x64",
        "version": version,
        "unsignedSha256": unsigned_hash,
        "signedSha256": signed_hash,
        "files": inventory,
        "recordSigned": False,
        "integrityVerified": True,
        "signatureVerificationPerformed": False,
        "clientQualified": False,
        "wackPassed": False,
        "releaseApproved": False,
        "gates": {gate: "NOT RUN" for gate in GATES},
        "evidenceAttached": {name: path is not None for name, path in optional.items()},
        "limitations": [
            "Hashes and matching supplied records do not authenticate origin or attestations.",
            "Signature bytes are not cryptographic verification or client trust.",
            "Installed metadata cannot establish which bytes are installed.",
            "The installed publisher-ID suffix is retained, not independently derived.",
            "WACK files are opaque attachments, not verified results or candidate binding.",
            "NOT RUN means not established by this assembler; review prior claims separately.",
            "No signer, tester, license owner or release approver is inferred.",
        ],
    }
    if _validate_only:
        return result
    output.mkdir(parents=True)
    for name, path in inputs.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        require(
            digest(target) == inventory[name]["sha256"]
            and digest(path) == inventory[name]["sha256"],
            "Evidence changed during assembly",
        )
    # Validate copied bytes/records again before publishing any success record.
    copied = assemble(
        output / "review",
        output / "_validation-only",
        edition=edition,
        source_sha=source_sha,
        run_url=run_url,
        signed_package=output / "signing" / signed_package.name if signed_package else None,
        signing_record=output / "signing/signing.json" if signing_record else None,
        client_preflight=output / "client/client-preflight.json" if client_preflight else None,
        installed_package=output / "client/installed-package.json" if installed_package else None,
        wack_xml=output / "wack/report.xml" if wack_xml else None,
        wack_html=output / "wack/report.html" if wack_html else None,
        _validate_only=True,
    )
    require(copied == result, "Copied evidence does not match validated inputs")
    lines = [
        "# Windows qualification evidence — NOT APPROVED",
        "",
        f"Edition: {edition}; identity: `{identity}`; version: `{version}`.",
        f"Source: `{source_sha}`; run: {run_url}.",
        f"Unsigned SHA-256: `{unsigned_hash}`.",
        f"Signed SHA-256: `{signed_hash or 'NOT PROVIDED'}`.",
        "",
        "Integrity reconciliation only. Owner/manual gates below are NOT RUN by this tool.",
        "Attachments and operator statements are not promoted to verified test results.",
        "",
        "| Gate | Status |",
        "| --- | --- |",
    ]
    lines += [f"| {gate} | NOT RUN |" for gate in GATES]
    lines += ["", *["- " + warning for warning in result["limitations"]], ""]
    (output / "QUALIFICATION.md").write_text("\n".join(lines), encoding="utf-8")
    (output / "qualification-evidence.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("review", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--edition", choices=sorted(IDENTITIES), required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--run-url", required=True)
    for name in (
        "signed-package",
        "signing-record",
        "client-preflight",
        "installed-package",
        "wack-xml",
        "wack-html",
    ):
        parser.add_argument("--" + name, type=Path)
    arguments = vars(parser.parse_args())
    try:
        assembled = assemble(**arguments)
    except (ValueError, OSError, zipfile.BadZipFile, ET.ParseError) as error:
        parser.exit(2, f"Evidence not qualified: {error}\n")
    print(f"Reconciled {len(assembled['files'])} files; signing/client/WACK/Store not approved.")
