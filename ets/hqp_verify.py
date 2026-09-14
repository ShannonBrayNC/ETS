"""Command-line entrypoint for the independent HQP verifier.

Run with ``python -m ets.hqp_verify`` from an installed ETS environment.
"""

from ets.qualification.verifier import main


if __name__ == "__main__":
    raise SystemExit(main())
