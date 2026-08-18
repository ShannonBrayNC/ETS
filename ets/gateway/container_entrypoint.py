"""Container entrypoint for the hosted ETS Gateway runtime."""

from __future__ import annotations

import uvicorn

from ets.gateway.hosted_runtime import create_app_from_env


def main() -> None:
    uvicorn.run(create_app_from_env(), host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
