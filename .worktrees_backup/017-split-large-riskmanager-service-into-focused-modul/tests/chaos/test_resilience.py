import os

import pytest


@pytest.mark.chaos
@pytest.mark.local_only
def test_resilience_suite_gate():
    if not os.getenv("RUN_CHAOS_TESTS"):
        pytest.skip("Set RUN_CHAOS_TESTS=1 to execute resilience tests.")

    assert True
