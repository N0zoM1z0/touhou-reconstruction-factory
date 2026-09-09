"""Base interfaces and deterministic repository adapter selection."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..errors import AdapterError
from ..ontology import RepositorySnapshot


class RepositoryAdapter(ABC):
    id: str

    @abstractmethod
    def detect(self, root: Path) -> bool:
        """Return true only when the repository satisfies this adapter signature."""

    @abstractmethod
    def inspect(self, root: Path) -> RepositorySnapshot:
        """Read and normalize a repository without mutating it or running its tools."""


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, RepositoryAdapter] = {}

    def register(self, adapter: RepositoryAdapter) -> None:
        if adapter.id in self._adapters:
            raise AdapterError(f"duplicate adapter id: {adapter.id}")
        self._adapters[adapter.id] = adapter

    def detect(self, root: str | Path) -> RepositoryAdapter:
        resolved = Path(root).resolve(strict=True)
        matches = [adapter for adapter in self._adapters.values() if adapter.detect(resolved)]
        if not matches:
            raise AdapterError(f"no repository adapter recognized {resolved}")
        if len(matches) > 1:
            names = ", ".join(sorted(adapter.id for adapter in matches))
            raise AdapterError(f"ambiguous repository adapters for {resolved}: {names}")
        return matches[0]

    def inspect(self, root: str | Path) -> RepositorySnapshot:
        resolved = Path(root).resolve(strict=True)
        return self.detect(resolved).inspect(resolved)


def require_repository_root(root: Path) -> Path:
    resolved = root.resolve(strict=True)
    if not resolved.is_dir():
        raise AdapterError(f"repository root is not a directory: {resolved}")
    return resolved

