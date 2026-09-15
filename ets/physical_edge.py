"""Command-line entrypoint for Wave 1 physical Edge Compact R0 bench bootstrap.

Run with ``python -m ets.physical_edge``.
"""

from ets.qualification.physical_edge import main

if __name__ == "__main__":
    raise SystemExit(main())
