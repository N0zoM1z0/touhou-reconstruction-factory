"""Read-only adapters for existing reconstruction repositories."""

from .base import AdapterRegistry, RepositoryAdapter
from .th04 import Th04RepositoryAdapter
from .windows import WindowsPeRepositoryAdapter


def builtin_adapters() -> AdapterRegistry:
    registry = AdapterRegistry()
    registry.register(Th04RepositoryAdapter())
    registry.register(WindowsPeRepositoryAdapter())
    return registry


def inspect_repository(path):
    return builtin_adapters().inspect(path)


__all__ = [
    "AdapterRegistry",
    "RepositoryAdapter",
    "Th04RepositoryAdapter",
    "WindowsPeRepositoryAdapter",
    "builtin_adapters",
    "inspect_repository",
]

