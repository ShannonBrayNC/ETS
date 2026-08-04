"""Version helpers for ETS."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


def get_version() -> str:
    """Return the installed ETS package version with a source-tree fallback."""

    try:
        return version("ets")
    except PackageNotFoundError:  # pragma: no cover - source tree before install
        return "0.1.0"


__version__ = get_version()

__all__ = ["__version__", "get_version"]
