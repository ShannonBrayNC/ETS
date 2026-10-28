"""Small native-dialog Developer bridge; verifier semantics stay in DesktopAPI."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ets.desktop.controller import DesktopAPI
from ets.desktop.sandbox import LOG_ID, create_sample

# Immutable alpha artifact from SDK PR #951. This pin is not release provenance.
SDK_KIT_SHA256 = "c12ab50a808b5266593ef731951a875dd5276a89fd7b963c82eabffbc44d03a7"
SDK_KIT_SIZE = 2034146
SDK_SOURCE_SHA = "a6eb2c70b4e84cdae5f6d88e788d2fb1f663fa3e"


class DeveloperAPI(DesktopAPI):
    """No path, code, network, private-key or trust-import arguments from HTML."""

    def __init__(
        self, choose: Callable[[str], str | None], command: list[str] | None = None,
        *, sdk_kit: Path | None = None,
    ) -> None:
        super().__init__(choose, command)
        self._sample: Path | None = None
        self._sdk_kit = sdk_kit or Path(__file__).with_name("assets") / "sdk-test-kit.zip"

    def _select(self, kind: str) -> dict[str, Any]:
        with self._lock:
            selected = self._choose(kind)
            if selected is None:
                return {"cancelled": True}
            if kind == "bundle":
                self._bundle = selected
                # Never carry sample trust across an external bundle selection.
                self._trust = None
                self._sample = None
            else:
                self._trust = selected
            self._outcome = None
            return {"name": Path(selected).name, "selected": True,
                    "trust_cleared": kind == "bundle"}

    def create_sample(self) -> dict[str, Any]:
        with self._lock:
            selected = self._choose("sample_parent")
            if selected is None:
                return {"cancelled": True}
            try:
                output = create_sample(Path(selected))
            except (OSError, ValueError, RuntimeError):
                return {"error": "Sample creation failed. Choose a writable local folder without "
                        "links. Any interrupted ETS-synthetic folder has no completion marker; "
                        "existing evidence and the previous selection are unchanged."}
            self._sample = output
            self._bundle = str(output / "bundle.json")
            self._trust = None
            self._outcome = None
            self._expected_log = LOG_ID
            return {"created": output.name, "bundle": "bundle.json",
                    "expected_log_id": LOG_ID, "sample_trust": False}

    def use_sample_trust(self) -> dict[str, Any]:
        with self._lock:
            if self._sample is None or self._bundle != str(self._sample / "bundle.json"):
                return {"error": "Create a synthetic sample first. No global trust is installed."}
            self._trust = str(self._sample / "sample-trust.json")
            self._outcome = None
            return {"name": "sample-trust.json", "selected": True}

    def export_sdk(self) -> dict[str, Any]:
        with self._lock:
            selected = self._choose("sdk_zip")
            if selected is None:
                return {"cancelled": True}
            try:
                # Bound memory and verify the complete exact archive before any output.
                with self._sdk_kit.open("rb") as stream:
                    payload = stream.read(SDK_KIT_SIZE + 1)
                if (len(payload) != SDK_KIT_SIZE
                        or hashlib.sha256(payload).hexdigest() != SDK_KIT_SHA256):
                    return {"error": "Bundled SDK kit integrity check failed. Nothing exported."}
            except OSError:
                return {"error": "This candidate is missing its SDK kit. Nothing exported."}
            try:
                with Path(selected).open("xb") as stream:
                    stream.write(payload)
            except OSError:
                return {"error": "Choose a new filename in a writable folder. Existing files "
                        "are protected. A failed write may leave an incomplete ZIP; retry "
                        "with a new filename."}
            return {"saved": Path(selected).name, "sha256": SDK_KIT_SHA256,
                    "source_sha": SDK_SOURCE_SHA}
