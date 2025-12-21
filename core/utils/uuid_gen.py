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

from __future__ import annotations

import uuid
from typing import Optional


DEFAULT_NAMESPACE = uuid.UUID("00000000-0000-0000-0000-000000000000")


class DeterministicUUIDGenerator:
    """Generates deterministic UUIDs for replay scenarios."""

    def __init__(self, seed: int = 0, namespace: uuid.UUID = DEFAULT_NAMESPACE):
        self._seed = seed
        self._counter = 0
        self._namespace = namespace

    def generate(self, name: Optional[str] = None) -> uuid.UUID:
        """Generate a deterministic UUID from a name or seed/counter."""
        if name is None:
            name = f"{self._seed}-{self._counter}"
            self._counter += 1
        return uuid.uuid5(self._namespace, name)

    def reset(self, seed: Optional[int] = None) -> None:
        """Reset the generator counter and optionally update the seed."""
        if seed is not None:
            self._seed = seed
        self._counter = 0


_DEFAULT_GENERATOR = DeterministicUUIDGenerator()


def generate_uuid(name: Optional[str] = None, seed: Optional[int] = None) -> str:
    """Generate a deterministic UUID string."""
    if seed is not None:
        generator = DeterministicUUIDGenerator(seed)
        return str(generator.generate(name))
    return str(_DEFAULT_GENERATOR.generate(name))


def generate_uuid_hex(
    name: Optional[str] = None, seed: Optional[int] = None, length: int = 8
) -> str:
    """Generate a deterministic UUID hex string with a specific length."""
    value = generate_uuid(name=name, seed=seed)
    return uuid.UUID(value).hex[:length]
