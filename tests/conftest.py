from __future__ import annotations

import os
from pathlib import Path

RUN_DATE = os.environ.setdefault("RUN_DATE", "local")

ARTIFACT_PATHS = [
    Path(f"backoffice/artifacts/{RUN_DATE}/unit"),
    Path(f"backoffice/artifacts/{RUN_DATE}/integration"),
    Path(f"backoffice/artifacts/{RUN_DATE}/security"),
    Path(f"backoffice/artifacts/{RUN_DATE}/lint"),
    Path(f"backoffice/artifacts/{RUN_DATE}/types"),
]


def pytest_configure() -> None:
    for path in ARTIFACT_PATHS:
        path.mkdir(parents=True, exist_ok=True)
