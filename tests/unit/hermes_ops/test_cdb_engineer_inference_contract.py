"""cdb-engineer ChatGPT/Codex subscription inference contract tests (#4501)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tools.hermes_ops.inference_contract import (
    FORBIDDEN_INFERENCE_ENV,
    REQUIRED_PRIMARY_PROVIDER,
    validate_cdb_engineer_config,
    validate_cdb_engineer_distribution,
)
from tools.hermes_ops.profiles import validate_profile

pytestmark = [pytest.mark.unit, pytest.mark.contract]

PROFILE_ROOT = Path("config/hermes/profiles/cdb-engineer")


def _load_engineer_files() -> tuple[dict, dict, str]:
    dist = yaml.safe_load(
        (PROFILE_ROOT / "distribution.yaml").read_text(encoding="utf-8")
    )
    cfg = yaml.safe_load((PROFILE_ROOT / "config.yaml").read_text(encoding="utf-8"))
    env_example = (PROFILE_ROOT / ".env.EXAMPLE").read_text(encoding="utf-8")
    return dist, cfg, env_example


def test_cdb_engineer_profile_validation_passes() -> None:
    report = validate_profile("cdb-engineer")
    assert report.ok, report.errors


def test_cdb_engineer_accepts_openai_codex_primary() -> None:
    dist, cfg, env_example = _load_engineer_files()
    assert dist["cdb"]["inference"]["primary_provider"] == REQUIRED_PRIMARY_PROVIDER
    assert cfg["model"]["provider"] == REQUIRED_PRIMARY_PROVIDER
    assert validate_cdb_engineer_distribution(dist, env_example_text=env_example) == []
    assert validate_cdb_engineer_config(cfg) == []


def test_cdb_engineer_oauth_path_needs_no_openai_or_openrouter_keys() -> None:
    dist, _cfg, env_example = _load_engineer_files()
    declared = {entry["name"] for entry in dist.get("env_requires") or []}
    assert "OPENAI_API_KEY" not in declared
    assert "OPENROUTER_API_KEY" not in declared
    for key in ("OPENAI_API_KEY", "OPENROUTER_API_KEY"):
        assert key not in declared
        assert f"{key}=" not in env_example
    assert dist["cdb"]["inference"]["paid_api_fallback"] is False


def test_cdb_engineer_rejects_openai_api_provider() -> None:
    _dist, cfg, _env = _load_engineer_files()
    bad = yaml.safe_load(yaml.safe_dump(cfg))
    bad["model"]["provider"] = "openai-api"
    errors = validate_cdb_engineer_config(bad)
    assert any("model.provider" in e for e in errors)


def test_cdb_engineer_rejects_openrouter_fallback() -> None:
    _dist, cfg, _env = _load_engineer_files()
    bad = yaml.safe_load(yaml.safe_dump(cfg))
    bad["fallback_providers"] = [{"provider": "openrouter", "model": "x"}]
    errors = validate_cdb_engineer_config(bad)
    assert any("fallback_providers" in e for e in errors)


def test_cdb_engineer_rejects_api_key_fallback_and_oauth_unavailable_paid_path() -> (
    None
):
    _dist, cfg, _env = _load_engineer_files()
    bad = yaml.safe_load(yaml.safe_dump(cfg))
    bad["fallback_providers"] = [{"provider": "openai-api", "model": "gpt-4o"}]
    errors = validate_cdb_engineer_config(bad)
    assert any("fail closed" in e or "fallback_providers" in e for e in errors)
    bad2 = yaml.safe_load(yaml.safe_dump(cfg))
    bad2["fallback_model"] = {"provider": "openrouter", "model": "x"}
    errors2 = validate_cdb_engineer_config(bad2)
    assert any("fallback_model" in e for e in errors2)


def test_cdb_engineer_rejects_ambiguous_auto_auxiliary() -> None:
    _dist, cfg, _env = _load_engineer_files()
    bad = yaml.safe_load(yaml.safe_dump(cfg))
    bad["auxiliary"]["compression"]["provider"] = "auto"
    errors = validate_cdb_engineer_config(bad)
    assert any("auxiliary.compression.provider" in e for e in errors)


def test_cdb_engineer_rejects_openrouter_in_distribution_env_requires() -> None:
    dist, _cfg, env_example = _load_engineer_files()
    bad = yaml.safe_load(yaml.safe_dump(dist))
    bad["env_requires"] = list(bad.get("env_requires") or []) + [
        {"name": "OPENROUTER_API_KEY", "required": False}
    ]
    errors = validate_cdb_engineer_distribution(bad, env_example_text=env_example)
    assert any("OPENROUTER_API_KEY" in e for e in errors)


def test_cdb_engineer_env_example_forbids_paid_inference_keys() -> None:
    _dist, _cfg, env_example = _load_engineer_files()
    for key in FORBIDDEN_INFERENCE_ENV:
        # Active declarations only (ignore comments mentioning the names).
        active_lines = [
            line
            for line in env_example.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        assert not any(line.startswith(f"{key}=") for line in active_lines)


def test_other_profiles_not_forced_off_openrouter() -> None:
    """jannek-assistant may still document optional OPENROUTER; do not regress."""
    personal = yaml.safe_load(
        Path("config/hermes/profiles/jannek-assistant/distribution.yaml").read_text(
            encoding="utf-8"
        )
    )
    names = {e["name"] for e in personal.get("env_requires") or []}
    assert "OPENROUTER_API_KEY" in names
