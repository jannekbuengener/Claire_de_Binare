"""
Seed Manager for deterministic random numbers.
Governance: CDB_PSM_POLICY.md (Replay-faehig)

relations:
  role: seed_manager
  domain: utility
  upstream:
    - governance/CDB_PSM_POLICY.md
  downstream:
    - tests/replay/test_deterministic_replay.py
"""

import random
from typing import Optional


class SeedManager:
    """Manager for deterministic seeding."""

    def __init__(self, seed: Optional[int] = None):
        self._seed = seed
        self._rng = random.Random(seed)  # Own RNG, not global

    def set_seed(self, seed: int) -> None:
        """Set a new seed."""
        self._seed = seed
        self._rng = random.Random(seed)

    def get_seed(self) -> Optional[int]:
        """Return the current seed."""
        return self._seed

    def random_int(self, min_val: int = 0, max_val: int = 1000000) -> int:
        """Generate a deterministic random integer."""
        return self._rng.randint(min_val, max_val)


_GLOBAL_SEED_MANAGER = SeedManager()


class Seed:
    """Lightweight wrapper around SeedManager for shared access."""

    _manager: SeedManager = _GLOBAL_SEED_MANAGER

    @classmethod
    def set(cls, seed: Optional[int]) -> None:
        """Set or clear the global seed used by tests."""
        cls._manager = SeedManager(seed)

    @classmethod
    def get(cls) -> Optional[int]:
        """Return the current global seed value."""
        return cls._manager.get_seed()

    @classmethod
    def random_int(cls, min_val: int = 0, max_val: int = 1000000) -> int:
        """Generate a deterministic random integer using the shared manager."""
        return cls._manager.random_int(min_val, max_val)
