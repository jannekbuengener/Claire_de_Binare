import os
import time

import pytest


@pytest.mark.local_only
@pytest.mark.slow
def test_baseline_smoke():
    if not os.getenv("PERF_BASELINE_RUN"):
        pytest.skip("Set PERF_BASELINE_RUN=1 to execute performance baselines.")

    start = time.perf_counter()
    time.sleep(0.01)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms < 1000
