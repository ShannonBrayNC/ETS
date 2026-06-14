"""Version helpers for ETS."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version

try:
    __version__ = package_version("ets")
except PackageNotFoundError:  # pragma: no cover - source tree before install
    __version__ = "0.1.0"

__all__ = ["__version__"]
