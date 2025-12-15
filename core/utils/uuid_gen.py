---
relations:
  role: uuid_generator
  domain: utility
  upstream:
    - governance/CDB_PSM_POLICY.md
  downstream:
    - core/domain/event.py
    - tests/replay/test_deterministic_replay.py
---
"""
Deterministic UUID Generator für Event-Sourcing Replay.
Governance: CDB_PSM_POLICY.md (Event-Sourcing, Determinismus)
"""

import uuid
import hashlib
from typing import Optional


class UUIDGenerator:
    """Generiert deterministische UUIDs für Replay."""

    def __init__(self, seed: Optional[int] = None):
        self._seed = seed
        self._counter = 0

    def generate(self) -> uuid.UUID:
        """Generiert UUID (deterministisch wenn Seed gesetzt)."""
        if self._seed is None:
            # Echtes UUID4 (Produktion)
            return uuid.uuid4()
        else:
            # Deterministisches UUID (Replay)
            return self.generate_deterministic_uuid(self._seed, self._counter)

    def generate_deterministic_uuid(self, seed: int, counter: int) -> uuid.UUID:
        """
        Generiert deterministisches UUID aus Seed + Counter.

        Args:
            seed: Basis-Seed
            counter: Sequenz-Counter

        Returns:
            UUID v5 (deterministisch)
        """
        # Hash aus Seed + Counter
        namespace = uuid.UUID('00000000-0000-0000-0000-000000000000')
        name = f"{seed}-{counter}"

        # Increment counter für nächsten Call
        self._counter += 1

        # UUID v5 (SHA1-basiert, deterministisch)
        return uuid.uuid5(namespace, name)
