"""Safety-flag parsing contract for the execution runtime."""

import pytest

from services.execution.config import _env_flag


@pytest.mark.unit
@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
def test_env_flag_accepts_explicit_true_spellings(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("CDB_TEST_SAFE_FLAG", value)
    assert _env_flag("CDB_TEST_SAFE_FLAG", "false") is True


@pytest.mark.unit
@pytest.mark.parametrize("value", ["0", "false", "", "unexpected"])
def test_env_flag_rejects_other_values(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("CDB_TEST_SAFE_FLAG", value)
    assert _env_flag("CDB_TEST_SAFE_FLAG", "true") is False
