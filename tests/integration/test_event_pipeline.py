"""Scaffold for future end-to-end pipeline tests."""

from __future__ import annotations

import pytest


@pytest.mark.integration
@pytest.mark.skip(reason="Integration pipeline scaffold; services not wired yet")
def test_event_pipeline_placeholder():
    """Placeholder for a Redis -> Risk -> Order pipeline test."""

    pytest.skip(
        "Integration pipeline requires Redis/Postgres; will connect once services "
        "are available"
    )


# TODO: Build full end-to-end test once the event pipeline is wired:
# 1. Emit a signal into Redis/event bus.
# 2. Risk engine evaluates and annotates the order request.
# 3. Execution component dispatches the resulting order to the exchange API.
