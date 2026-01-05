"""Skeleton for the 72h validation pipeline."""

from __future__ import annotations

from typing import Sequence


def assemble_pipeline(collectors: Sequence[str]) -> None:
    """Placeholder: orchestrate collectors feeding the 72h window."""
    # TODO: hook up metrics aggregation + scheduling
    if not collectors:
        raise ValueError("At least one collector must be configured")
