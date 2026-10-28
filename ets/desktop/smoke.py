"""Engineering-only native UI exercise; real dialogs remain a manual release gate."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class NativeSmoke:
    """Use a copied fixture and temporary reports, never modify the supplied fixture."""

    def __init__(self, fixture: Path, directory: Path, trust: Path | None = None) -> None:
        self.bundle = directory / "evidence bundle.json"
        self.bundle.write_bytes(fixture.read_bytes())
        self.report = directory / "verification report.json"
        self.trust = directory / "trusted keys.json" if trust is not None else None
        if trust is not None and self.trust is not None:
            self.trust.write_bytes(trust.read_bytes())

    def choose(self, kind: str) -> str | None:
        selected = {"bundle": self.bundle, "json": self.report, "trust": self.trust}.get(kind)
        return str(selected) if selected is not None else None

    @staticmethod
    def wait(window: Any, expression: str) -> None:
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            if window.evaluate_js(expression) is True:
                return
            time.sleep(0.1)
        raise RuntimeError("Native verification smoke condition timed out: " + expression)

    def run(self, window: Any) -> None:
        self.wait(window, "document.getElementById('bundle').disabled === false")
        window.evaluate_js("document.getElementById('bundle').click()")
        self.wait(window, "document.getElementById('verify').disabled === false")
        window.evaluate_js("document.getElementById('verify').click()")
        self.wait(window, "document.getElementById('status').dataset.state === 'indeterminate'"
                  " && document.querySelector('[data-format=json]').disabled === false")
        displayed = json.loads(window.evaluate_js("document.getElementById('raw').textContent"))
        window.evaluate_js("document.querySelector('[data-format=json]').click()")
        self.wait(window, "document.getElementById('message').textContent === "
                  "'Saved verification report.json' && "
                  "document.querySelector('[data-format=json]').disabled === false")
        original = self.report.read_bytes()
        exported = json.loads(original)
        if (exported['outcome'] != displayed
                or exported['policy']['require_tree_head_signature'] is not True):
            raise RuntimeError("Native export did not preserve the strict displayed outcome")
        # Existing output must be protected through the actual bridge, too.
        window.evaluate_js("document.querySelector('[data-format=json]').click()")
        self.wait(window, "document.getElementById('message').textContent.includes("
                  "'Existing files are protected')")
        if self.report.read_bytes() != original:
            raise RuntimeError("Native export overwrote the existing report")
        if self.trust is not None:
            window.evaluate_js("document.getElementById('trust').click()")
            self.wait(window, "document.getElementById('raw').textContent === 'No result yet.'"
                      " && document.getElementById('verify').disabled === false")
            window.evaluate_js("document.getElementById('verify').click()")
            self.wait(window, "document.getElementById('status').dataset.state === 'valid'"
                      " && document.querySelector('[data-format=json]').disabled === false")
            signed = json.loads(window.evaluate_js("document.getElementById('raw').textContent"))
            if (signed.get('signature_verified') is not True
                    or signed.get('continuity_verified') is not False
                    or signed.get('standing_status') != 'checkpoint_only'):
                raise RuntimeError("Signed result did not retain checkpoint-only trust semantics")
            self.report = self.report.with_name('signed report.json')
            window.evaluate_js("document.querySelector('[data-format=json]').click()")
            self.wait(window, "document.getElementById('message').textContent === "
                      "'Saved signed report.json' && "
                      "document.querySelector('[data-format=json]').disabled === false")
            signed_export = json.loads(self.report.read_bytes())
            if (signed_export['outcome'] != signed
                    or signed_export['policy']['require_tree_head_signature'] is not True):
                raise RuntimeError("Signed export did not match the displayed strict result")
            payload = json.loads(self.bundle.read_bytes())
            payload['event']['metadata']['tampered'] = True
            self.bundle.write_text(json.dumps(payload), encoding='utf-8')
            window.evaluate_js("document.getElementById('bundle').click()")
            self.wait(window, "document.getElementById('raw').textContent === 'No result yet.'"
                      " && document.getElementById('verify').disabled === false")
            window.evaluate_js("document.getElementById('verify').click()")
            self.wait(window, "document.getElementById('status').dataset.state === 'invalid'"
                      " && document.getElementById('verify').disabled === false")
        self.bundle.write_text('{', encoding='utf-8')
        window.evaluate_js("document.getElementById('bundle').click()")
        self.wait(window, "document.getElementById('raw').textContent === 'No result yet.'"
                  " && document.getElementById('verify').disabled === false")
        if window.evaluate_js("document.querySelector('[data-format=json]').disabled") is not True:
            raise RuntimeError("Selection did not invalidate the old export")
        window.evaluate_js("document.getElementById('verify').click()")
        self.wait(window, "document.getElementById('status').dataset.state === 'malformed'"
                  " && document.getElementById('verify').disabled === false")
