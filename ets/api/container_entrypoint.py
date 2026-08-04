"""Container entrypoint for ETS API runtime startup."""

from __future__ import annotations

import uvicorn

from ets.api.profile_guard import validate_environment


def main() -> None:
    validate_environment()
    uvicorn.run("ets.api.app:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
