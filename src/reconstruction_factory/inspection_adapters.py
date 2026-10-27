"""Control-plane imports that grant no new replay execution authority.

Keep the replay adapter registry and implementation fingerprint unchanged when
adding inventory-only repositories. A later reviewed replay implementation must
explicitly adopt their native source, extent and acceptance contracts.
"""

from pathlib import Path

from .adapters import inspect_repository as inspect_replay_repository
from .adapters.inventory import PeInventoryRepositoryAdapter, Th05ManifestRepositoryAdapter
from .ontology import RepositorySnapshot


def inspect_repository(path: str | Path) -> RepositorySnapshot:
    root = Path(path).resolve(strict=True)
    for adapter in (PeInventoryRepositoryAdapter(), Th05ManifestRepositoryAdapter()):
        if adapter.detect(root):
            return adapter.inspect(root)
    return inspect_replay_repository(root)
