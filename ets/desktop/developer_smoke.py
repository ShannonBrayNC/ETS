"""Engineering native smoke; does not replace clean Windows client qualification."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ets.desktop.developer import SDK_KIT_SHA256
from ets.desktop.smoke import NativeSmoke


class DeveloperSmoke:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.bundle: Path | None = None
        self.trust: Path | None = None
        self.report = directory / "developer report.json"
        self.kit = directory / "exported SDK kit.zip"

    def choose(self, kind: str) -> str | None:
        value = {"sample_parent": self.directory, "bundle": self.bundle,
                 "trust": self.trust, "json": self.report, "sdk_zip": self.kit}.get(kind)
        return str(value) if value is not None else None

    def run(self, window: Any) -> None:
        wait = NativeSmoke.wait
        wait(window, "document.getElementById('create-sample').disabled === false")
        window.evaluate_js("document.getElementById('create-sample').click()")
        wait(window, "document.getElementById('verify').disabled === false")
        samples = list(self.directory.glob("ETS-synthetic-*"))
        if len(samples) != 1 or not (samples[0] / "sample-summary.json").is_file():
            raise RuntimeError("Developer sample was not completely created")
        sample = samples[0]
        summary = json.loads((sample / "sample-summary.json").read_text(encoding="utf-8"))
        if (summary.get("creation_complete") is not True
                or summary.get("private_key_saved") is not False
                or summary.get("schema") != "ets.desktop_synthetic_sample.v1"
                or len(summary.get("sha256", {})) != 6):
            raise RuntimeError("Developer sample completion marker is invalid")
        for name, digest in summary["sha256"].items():
            if hashlib.sha256((sample / name).read_bytes()).hexdigest() != digest:
                raise RuntimeError("Developer sample payload differs from its completion marker")
        self.trust = sample / "sample-trust.json"
        window.evaluate_js("document.getElementById('verify').click()")
        wait(window, "document.getElementById('status').dataset.state === 'indeterminate'"
             " && document.getElementById('sample-trust').disabled === false")
        window.evaluate_js("document.getElementById('sample-trust').click()")
        wait(window, "document.getElementById('raw').textContent === 'No result yet.'"
             " && document.getElementById('verify').disabled === false")
        window.evaluate_js("document.getElementById('verify').click()")
        wait(window, "document.getElementById('status').dataset.state === 'valid'"
             " && document.querySelector('[data-format=json]').disabled === false")
        outcome = json.loads(window.evaluate_js("document.getElementById('raw').textContent"))
        if (outcome.get("signature_verified") is not True
                or outcome.get("standing_status") != "checkpoint_only"
                or outcome.get("continuity_verified") is not False):
            raise RuntimeError("Developer changed strict checkpoint-only semantics")
        window.evaluate_js("document.querySelector('[data-format=json]').click()")
        wait(window, "document.getElementById('message').textContent.includes('Saved ')")
        report_bytes = self.report.read_bytes()
        report = json.loads(report_bytes)
        if report["outcome"] != outcome or not report["policy"]["require_tree_head_signature"]:
            raise RuntimeError("Developer report differs from strict displayed result")
        window.evaluate_js("document.querySelector('[data-format=json]').click()")
        wait(window, "document.getElementById('message').textContent.includes('Existing files')")
        if self.report.read_bytes() != report_bytes:
            raise RuntimeError("Developer overwrote an existing report")
        window.evaluate_js("document.getElementById('sdk-export').click()")
        wait(window, "document.getElementById('sdk-message').textContent.includes('Saved ')"
             " && document.getElementById('sdk-export').disabled === false")
        if hashlib.sha256(self.kit.read_bytes()).hexdigest() != SDK_KIT_SHA256:
            raise RuntimeError("Developer exported different SDK bytes")
        window.evaluate_js("document.getElementById('sdk-export').click()")
        wait(window, "document.getElementById('sdk-message').textContent.includes('Existing files')"
             " && document.getElementById('sdk-export').disabled === false")
        if hashlib.sha256(self.kit.read_bytes()).hexdigest() != SDK_KIT_SHA256:
            raise RuntimeError("Developer overwrote the existing SDK export")
        self.bundle = sample / "tampered-bundle.json"
        window.evaluate_js("document.getElementById('bundle').click()")
        wait(window, "document.getElementById('raw').textContent === 'No result yet.'"
             " && document.getElementById('trust').disabled === false")
        window.evaluate_js("document.getElementById('trust').click()")
        wait(window, "document.getElementById('trust-name').textContent === 'sample-trust.json'"
             " && document.getElementById('verify').disabled === false")
        window.evaluate_js("document.getElementById('verify').click()")
        wait(window, "document.getElementById('status').dataset.state === 'invalid'")
