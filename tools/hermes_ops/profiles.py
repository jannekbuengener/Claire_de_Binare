"""Validate Hermes profile distributions in config/hermes (#4289)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from tools.hermes_ops.inference_contract import (
    validate_cdb_engineer_config,
    validate_cdb_engineer_distribution,
)
from tools.hermes_ops.policy import validate_distribution_cdb_block

REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILES_ROOT = REPO_ROOT / "config" / "hermes" / "profiles"
REQUIRED_PROFILES = ("jannek-assistant", "cdb-engineer", "validation-chief")
REQUIRED_FILES = (
    "distribution.yaml",
    "SOUL.md",
    "config.yaml",
    "AGENTS.md",
    ".gitignore",
    ".env.EXAMPLE",
)


@dataclass
class ProfileReport:
    profile: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must be a mapping")
    return data


def validate_profile(profile: str) -> ProfileReport:
    report = ProfileReport(profile=profile)
    root = PROFILES_ROOT / profile
    if not root.is_dir():
        report.errors.append(f"missing profile directory: {root}")
        return report
    for rel in REQUIRED_FILES:
        if not (root / rel).is_file():
            report.errors.append(f"missing required file: {rel}")
    dist_path = root / "distribution.yaml"
    cfg_path = root / "config.yaml"
    if dist_path.is_file():
        try:
            dist = _load_yaml(dist_path)
        except (OSError, ValueError, yaml.YAMLError) as exc:
            report.errors.append(f"distribution.yaml parse error: {exc}")
            dist = {}
        if dist.get("name") != profile:
            report.errors.append("distribution.name must match directory name")
        cdb = dist.get("cdb") or {}
        if not isinstance(cdb, dict):
            report.errors.append("distribution.cdb must be a mapping")
        else:
            report.errors.extend(validate_distribution_cdb_block(cdb, profile))
            if profile == "cdb-engineer":
                env_example = root / ".env.EXAMPLE"
                env_text = (
                    env_example.read_text(encoding="utf-8")
                    if env_example.is_file()
                    else ""
                )
                report.errors.extend(
                    validate_cdb_engineer_distribution(dist, env_example_text=env_text)
                )
    if cfg_path.is_file():
        try:
            cfg = _load_yaml(cfg_path)
        except (OSError, ValueError, yaml.YAMLError) as exc:
            report.errors.append(f"config.yaml parse error: {exc}")
            cfg = {}
        security = cfg.get("security") or {}
        if security.get("redact_secrets") is not True:
            report.errors.append("config.yaml security.redact_secrets must be true")
        server = cfg.get("server") or {}
        if server.get("host") not in {"127.0.0.1", "localhost", "::1"}:
            report.errors.append("server.host must be loopback")
        if server.get("require_auth_non_loopback") is not True:
            report.errors.append("require_auth_non_loopback must be true")
        if profile == "cdb-engineer" and cfg:
            report.errors.extend(validate_cdb_engineer_config(cfg))
    # Skills directory optional but if present must contain SKILL.md files only as docs.
    skills = root / "skills"
    if skills.is_dir():
        skill_mds = list(skills.rglob("SKILL.md"))
        if not skill_mds:
            report.warnings.append("skills/ present but no SKILL.md found")
    # Runtime leftovers must not be committed.
    for banned in ("memories", "sessions", ".env", "state.db"):
        if (root / banned).exists():
            report.errors.append(f"banned runtime path present in repo: {banned}")
    return report


def validate_all_profiles() -> list[ProfileReport]:
    reports = [validate_profile(name) for name in REQUIRED_PROFILES]
    # Ensure personal and engineering homes are isolated concepts in distributions.
    personal = PROFILES_ROOT / "jannek-assistant" / "distribution.yaml"
    engineer = PROFILES_ROOT / "cdb-engineer" / "distribution.yaml"
    if personal.is_file() and engineer.is_file():
        p = _load_yaml(personal)
        e = _load_yaml(engineer)
        if p.get("cdb", {}).get("profile_class") == e.get("cdb", {}).get(
            "profile_class"
        ):
            reports[0].errors.append(
                "profile_class must differ across personal/engineering"
            )
    return reports


def all_profiles_ok() -> bool:
    return all(r.ok for r in validate_all_profiles())
