"""Resolve disease terms to stable vocabulary-backed concepts."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("disease-normalizer")
except PackageNotFoundError:
    __version__ = "unknown"
finally:
    del version, PackageNotFoundError
