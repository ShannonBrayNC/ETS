"""Evidence Transparency System package."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("ets")
except PackageNotFoundError:  # pragma: no cover - source tree before install
    __version__ = "0.1.0"

__all__ = ["__version__", "api", "core", "verifier"]
