"""CLI entry point for HQP cross-product reuse validation."""

from __future__ import annotations

import argparse
from pathlib import Path

from ets.qualification.profile import HardwareQualificationProfile
from ets.qualification.reuse import load_reuse_manifest, render_reuse_summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an ETS HQP cross-product reuse binding")
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args(argv)

    profile = HardwareQualificationProfile.model_validate_json(args.profile.read_bytes())
    manifest = load_reuse_manifest(args.manifest.read_bytes())
    print(render_reuse_summary(profile, manifest), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
