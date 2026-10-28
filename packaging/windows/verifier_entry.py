"""Frozen CLI entry point; desktop UI and MSIX identity are separate release gates."""

from ets.verifier.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
