"""Command-line entrypoint for the ETS Edge HQP-3 corpus tooling.

Run with ``python -m ets.edge_hqp``.
"""

from ets.qualification.edge_corpus import main

if __name__ == "__main__":
    raise SystemExit(main())
