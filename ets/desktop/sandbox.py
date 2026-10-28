"""Bounded, synthetic-only authoring through the existing local SDK/core.

This is not a project importer or a production issuer. An ephemeral sample key is
never written, and the exported public key is never automatically trusted.
"""

from __future__ import annotations

import copy
import hashlib
import json
import stat
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from ets.core.bundle import EvidenceProofBundle
from ets.core.log import InMemoryAppendOnlyLog
from ets.core.proofs import generate_inclusion_proof
from ets.core.signing import Ed25519TreeHeadSigner
from ets.core.tree_head import SignedTreeHead
from ets.reports.strict import write_new_report
from ets.sdk.local import append_evidence, create_evidence, hash_evidence, verify_inclusion_proof

LOG_ID = "ets-desktop-synthetic"
KEY_ID = "ephemeral-sample-key-not-production"


def _write_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=True, allow_nan=False)
        stream.write("\n")


def create_sample(parent: Path) -> Path:
    """Reserve a fresh child of a native-picker folder; never touch existing files.

No user payloads, scripts, endpoints, key inputs, or arbitrary project manifests
are accepted. The small fixed fixture avoids exposing unbounded authoring inputs.
An interrupted write can leave a partial child, but never a completion marker.
"""
    parent = parent.absolute()
    if sys.platform == "win32":
        import ctypes

        # Reject UNC and mapped network drives before touching their contents.
        # Native folder selection is not authority for the sandbox to contact a share.
        if (parent.drive.startswith("\\\\")
                or ctypes.windll.kernel32.GetDriveTypeW(str(parent.anchor)) not in {2, 3, 6}):
            raise ValueError("Choose a local fixed, removable or RAM drive")
    for ancestor in (parent, *parent.parents):
        info = ancestor.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("Choose a local folder without links or reparse points")
    if not parent.is_dir():
        raise ValueError("Choose an existing folder")
    output = Path(tempfile.mkdtemp(prefix="ETS-synthetic-", dir=parent))
    now = datetime.now(UTC)
    key = Ed25519PrivateKey.generate()
    artifact = b"SYNTHETIC manufacturing inspection: sample part passed; not a real record\n"
    with (output / "synthetic-artifact.txt").open("xb") as stream:
        stream.write(artifact)
    event = create_evidence(
        {
            "event_id": "evt_desktop_synthetic_01",
            "tenant_id": "synthetic-tenant",
            "workspace_id": "desktop-sandbox",
            "evidence_id": "evidence_desktop_synthetic_01",
            "event_type": "synthetic.inspection",
            "subject_ref": "synthetic:part-001",
            "content_hash": hashlib.sha256(artifact).hexdigest(),
            "content_hash_alg": "sha256",
            "metadata": {
                "synthetic": True,
                "result": "pass",
                "claim_limit": "Demonstration only; not physical truth or regulatory compliance",
            },
            "created_at_utc": now,
            "source_system": "desktop-synthetic-sandbox",
            "correlation_id": "synthetic-workflow-01",
        }
    )
    store = InMemoryAppendOnlyLog()
    entry = append_evidence(store, event)
    if entry.event_hash != hash_evidence(event):
        raise RuntimeError("Local SDK event hash mismatch")
    proof = generate_inclusion_proof(store.list_entries(), entry.log_index, now)
    head = Ed25519TreeHeadSigner(key.private_bytes_raw().hex(), KEY_ID).sign(
        SignedTreeHead(
            tree_size=proof.tree_size, root_hash=proof.root_hash, created_at_utc=now, log_id=LOG_ID
        )
    )
    bundle = EvidenceProofBundle(
        event=event,
        event_hash=entry.event_hash,
        leaf_hash=entry.leaf_hash,
        tree_head=head,
        inclusion_proof=proof,
        verification_result=verify_inclusion_proof(proof),
    ).model_dump(mode="json")
    trust = {
        "keys": [{"key_id": KEY_ID, "signature_alg": "ed25519",
                  "public_key_hex": key.public_key().public_bytes_raw().hex()}]
    }
    _write_json(output / "event.json", event.model_dump(mode="json"))
    _write_json(output / "bundle.json", bundle)
    _write_json(output / "sample-trust.json", trust)
    tampered = copy.deepcopy(bundle)
    tampered["event"]["metadata"]["tampered_after_commit"] = True
    _write_json(output / "tampered-bundle.json", tampered)
    with (output / "README.txt").open("x", encoding="utf-8") as stream:
        stream.write(
            "SYNTHETIC SAMPLE ONLY. No customer data or production identity.\n"
            "The ephemeral private key was not saved. sample-trust.json is only\n"
            "the generated public test key; it is NOT independent production trust.\n"
            "Verify bundle.json without trust: indeterminate. Explicitly select\n"
            "sample-trust.json and expected log ets-desktop-synthetic: valid at\n"
            "checkpoint only. tampered-bundle.json with this key: invalid.\n"
            "Verification checks the bundle, not the separate artifact's bytes.\n"
            "No current continuity, completeness, real-world truth, or legal sufficiency.\n"
            "Reports are separate unsigned observations of computed strict results.\n"
            "Folders belong to you and are not removed on app uninstall.\n"
            "sample-summary.json is written last; without it creation was interrupted.\n"
        )
    hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(output.iterdir())
    }
    summary = {
        "schema": "ets.desktop_synthetic_sample.v1",
        "synthetic_only": True,
        "creation_complete": True,
        "private_key_saved": False,
        "expected_log_id": LOG_ID,
        "sha256": hashes,
    }
    # Publish the completion marker atomically, only after all payload writes.
    # Like report export, filesystems without hard-link support fail closed.
    write_new_report(
        output / "sample-summary.json",
        json.dumps(summary, indent=2, ensure_ascii=True, allow_nan=False) + "\n",
    )
    return output
