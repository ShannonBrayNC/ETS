"""Container entrypoint for the private ETS Fleet C3B runtime."""

from __future__ import annotations

import uvicorn

from ets.fleet.production_runtime import create_production_fleet_app


def main() -> None:
    uvicorn.run(
        create_production_fleet_app(),
        host="0.0.0.0",
        port=8080,
        proxy_headers=False,
        server_header=False,
    )


if __name__ == "__main__":
    main()
