"""
Deterministic UUID Generator for Event-Sourcing Replay.
Governance: CDB_PSM_POLICY.md (Event-Sourcing, Determinismus)

relations:
  role: uuid_generator
  domain: utility
  upstream:
    - governance/CDB_PSM_POLICY.md
  downstream:
    - core/domain/event.py
    - tests/replay/test_deterministic_replay.py
"""

import uuid
import hashlib
from typing import Optional


class UUIDGenerator:
    """Generates deterministic UUIDs for replay scenarios."""

    def __init__(self, seed: Optional[int] = None):
        self._seed = seed
        self._counter = 0

    def generate(self) -> uuid.UUID:
        """Generate a UUID (deterministic when a seed is set)."""
        if self._seed is None:
            return uuid.uuid4()
        return self.generate_deterministic_uuid(self._seed, self._counter)

    def generate_deterministic_uuid(self, seed: int, counter: int) -> uuid.UUID:
        """Generate a deterministic UUID derived from seed and counter."""
        namespace = uuid.UUID("00000000-0000-0000-0000-000000000000")
        name = f"{seed}-{counter}"

        # Increment counter for next call
        self._counter += 1

        return uuid.uuid5(namespace, name)


def generate_uuid(deterministic: bool = False, seed: Optional[int] = None) -> str:
    """Convenience wrapper to generate either random or deterministic UUIDs."""
    if deterministic:
        generator = UUIDGenerator(seed if seed is not None else 0)
        return str(generator.generate())
    return str(uuid.uuid4())
