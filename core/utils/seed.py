"""
Seed Manager für deterministische Zufallszahlen.
Governance: CDB_PSM_POLICY.md (Replay-fähig)
"""

import random
from typing import Optional


class SeedManager:
    """Manager für deterministisches Seeding."""

    def __init__(self, seed: Optional[int] = None):
        self._seed = seed
        self._rng = random.Random(seed)  # Eigener RNG, nicht global

    def set_seed(self, seed: int):
        """Setzt neuen Seed."""
        self._seed = seed
        self._rng = random.Random(seed)

    def get_seed(self) -> Optional[int]:
        """Liefert aktuellen Seed."""
        return self._seed

    def random_int(self, min_val: int = 0, max_val: int = 1000000) -> int:
        """Generiert deterministische Zufallszahl."""
        return self._rng.randint(min_val, max_val)
