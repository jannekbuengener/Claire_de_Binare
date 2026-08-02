"""Profile distribution contract tests for Hermes (#4289)."""

from __future__ import annotations

import pytest

from tools.hermes_ops.profiles import validate_all_profiles, validate_profile

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_required_profiles_validate() -> None:
    reports = validate_all_profiles()
    assert {r.profile for r in reports} == {
        "jannek-assistant",
        "cdb-engineer",
        "validation-chief",
    }
    assert all(r.ok for r in reports), {
        r.profile: r.errors for r in reports if not r.ok
    }


def test_personal_profile_has_no_github_write() -> None:
    report = validate_profile("jannek-assistant")
    assert report.ok
    from pathlib import Path
    import yaml

    dist = yaml.safe_load(
        (Path("config/hermes/profiles/jannek-assistant/distribution.yaml")).read_text(
            encoding="utf-8"
        )
    )
    assert dist["cdb"]["github_write"] is False
    assert dist["cdb"]["windows_access"] is False


def test_engineer_reuses_auth_lineage_and_scopes_repos() -> None:
    import yaml
    from pathlib import Path

    dist = yaml.safe_load(
        Path("config/hermes/profiles/cdb-engineer/distribution.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert dist["cdb"]["allowed_repositories"] == [
        "jannekbuengener/Claire_de_Binare"
    ]  # pragma: allowlist secret
    assert "4170" in {str(x) for x in dist["cdb"]["reuses_auth_lineage"]}
    assert dist["cdb"]["cdb_local_ci_publish"] is False
    assert dist["cdb"]["merge_authority"] is False


def test_validation_chief_disabled_by_default() -> None:
    import yaml
    from pathlib import Path

    dist = yaml.safe_load(
        Path("config/hermes/profiles/validation-chief/distribution.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert dist["cdb"]["enabled_by_default"] is False
