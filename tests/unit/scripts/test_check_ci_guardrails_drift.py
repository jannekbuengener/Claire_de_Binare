"""Tests for check_ci_guardrails_drift.py."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts" / "governance"))

from check_ci_guardrails_drift import (
    evaluate_ci_workflow,
    evaluate_e2e_workflow,
    evaluate_gitleaks_workflow,
    evaluate_legacy_ci_workflow,
    evaluate_sentinel_workflow,
    load_workflow,
)


def test_current_repo_workflows_satisfy_guardrails() -> None:
    ci_payload = load_workflow(Path(".github/workflows/ci.yml"))
    gitleaks_payload = load_workflow(Path(".github/workflows/gitleaks.yml"))
    legacy_ci_payload = load_workflow(Path(".github/workflows/ci.yaml"))
    e2e_payload = load_workflow(Path(".github/workflows/e2e.yml"))
    e2e_tests_payload = load_workflow(Path(".github/workflows/e2e-tests.yml"))
    shadow_soak_payload = load_workflow(
        Path(".github/workflows/shadow-soak-evidence.yml")
    )
    sentinel_payload = load_workflow(
        Path(".github/workflows/required-checks-audit.yml")
    )

    ci_failures = [
        finding
        for finding in evaluate_ci_workflow(ci_payload)
        if finding.status == "FAIL"
    ]
    gitleaks_failures = [
        finding
        for finding in evaluate_gitleaks_workflow(gitleaks_payload)
        if finding.status == "FAIL"
    ]
    legacy_ci_failures = [
        finding
        for finding in evaluate_legacy_ci_workflow(legacy_ci_payload)
        if finding.status == "FAIL"
    ]
    sentinel_failures = [
        finding
        for finding in evaluate_sentinel_workflow(sentinel_payload)
        if finding.status == "FAIL"
    ]
    e2e_failures = [
        finding
        for finding in evaluate_e2e_workflow(
            e2e_payload,
            ".github/workflows/e2e.yml",
            "Create CI secrets directory",
        )
        if finding.status == "FAIL"
    ]
    e2e_tests_failures = [
        finding
        for finding in evaluate_e2e_workflow(
            e2e_tests_payload,
            ".github/workflows/e2e-tests.yml",
            "Create CI Secrets Directory",
        )
        if finding.status == "FAIL"
    ]
    shadow_soak_failures = [
        finding
        for finding in evaluate_e2e_workflow(
            shadow_soak_payload,
            ".github/workflows/shadow-soak-evidence.yml",
            "Create CI secrets",
        )
        if finding.status == "FAIL"
    ]

    assert ci_failures == []
    assert gitleaks_failures == []
    assert legacy_ci_failures == []
    assert sentinel_failures == []
    assert e2e_failures == []
    assert e2e_tests_failures == []
    assert shadow_soak_failures == []


def test_guard_detects_missing_pr_secret_scan_and_black_step(tmp_path: Path) -> None:
    bad_gitleaks = tmp_path / "gitleaks.yml"
    bad_gitleaks.write_text(
        """
name: Gitleaks Secret Scan
on:
  push:
    branches: [main]
jobs:
  gitleaks:
    name: gitleaks (Secrets-Alarm)
    continue-on-error: true
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 1
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITLEAKS_CONFIG: wrong.toml
""".strip(),
        encoding="utf-8",
    )

    bad_ci = tmp_path / "ci.yml"
    bad_ci.write_text(
        """
name: ci
on:
  pull_request:
    branches: [main]
jobs:
  ci:
    steps:
      - name: Ruff
        run: ruff format .
""".strip(),
        encoding="utf-8",
    )

    gitleaks_failures = {
        finding.rule
        for finding in evaluate_gitleaks_workflow(load_workflow(bad_gitleaks))
        if finding.status == "FAIL"
    }
    ci_failures = {
        finding.rule
        for finding in evaluate_ci_workflow(load_workflow(bad_ci))
        if finding.status == "FAIL"
    }

    assert "pull_request branch scope" in gitleaks_failures
    assert "fail-closed job behavior" in gitleaks_failures
    assert "full-history checkout" in gitleaks_failures
    assert "repo gitleaks config" in gitleaks_failures
    assert "Black step present" in ci_failures
    assert "Black command" in ci_failures


def test_guard_detects_e2e_stub_drift(tmp_path: Path) -> None:
    bad_e2e = tmp_path / "e2e.yml"
    bad_e2e.write_text(
        """
name: E2E
on:
  workflow_dispatch:
jobs:
  e2e_smoke:
    steps:
      - name: Preflight required secrets (REAL vs STUB)
        env:
          SMTP_FROM: ${{ secrets.SMTP_FROM }}
          SMTP_HOST: ${{ secrets.SMTP_HOST }}
          SMTP_USER: ${{ secrets.SMTP_USER }}
          SMTP_PASSWORD: ${{ secrets.SMTP_PASSWORD }}
          ALERT_EMAIL_TO: ${{ secrets.ALERT_EMAIL_TO }}
          MEXC_API_KEY: ${{ secrets.MEXC_API_KEY }}
          MEXC_API_SECRET: ${{ secrets.MEXC_API_SECRET }}
        run: |
          required=(SMTP_FROM SMTP_HOST SMTP_USER SMTP_PASSWORD ALERT_EMAIL_TO MEXC_API_KEY MEXC_API_SECRET)
      - name: Fail closed on protected STUB mode
        if: steps.preflight.outputs.protected_context == 'true'
        run: echo "bad"
      - name: Create CI secrets directory
        env:
          SMTP_FROM_SECRET: ${{ secrets.SMTP_FROM }}
          SMTP_HOST_SECRET: ${{ secrets.SMTP_HOST }}
          SMTP_USER_SECRET: ${{ secrets.SMTP_USER }}
          SMTP_PASSWORD_SECRET: ${{ secrets.SMTP_PASSWORD }}
          ALERT_EMAIL_TO_SECRET: ${{ secrets.ALERT_EMAIL_TO }}
          MEXC_API_KEY_SECRET: ${{ secrets.MEXC_API_KEY }}
          MEXC_API_SECRET_SECRET: ${{ secrets.MEXC_API_SECRET }}
        run: |
          REDIS_VAL="${{ secrets.REDIS_PASSWORD != '' && secrets.REDIS_PASSWORD || 'ci-redis-password' }}"
          POSTGRES_VAL="${{ secrets.POSTGRES_PASSWORD != '' && secrets.POSTGRES_PASSWORD || 'ci-postgres-password' }}"
          GRAFANA_VAL="${{ secrets.GRAFANA_PASSWORD != '' && secrets.GRAFANA_PASSWORD || 'ci-grafana-password' }}"
""".strip(),
        encoding="utf-8",
    )

    e2e_failures = {
        finding.rule
        for finding in evaluate_e2e_workflow(
            load_workflow(bad_e2e),
            ".github/workflows/e2e.yml",
            "Create CI secrets directory",
        )
        if finding.status == "FAIL"
    }

    assert "preflight secret env mapping" in e2e_failures
    assert "preflight required secret list" in e2e_failures
    assert "protected STUB hard fail condition" in e2e_failures
    assert "protected STUB hard fail message" in e2e_failures
    assert "non-protected STUB visibility step" in e2e_failures
    assert "create secrets env mapping" in e2e_failures
    assert "forbidden inline secret fallbacks" in e2e_failures
    assert "REAL materialization guard" in e2e_failures


def test_guard_detects_legacy_restore_green_drift(tmp_path: Path) -> None:
    bad_legacy_ci = tmp_path / "ci.yaml"
    bad_legacy_ci.write_text(
        """
name: CI/CD Pipeline
on:
  push:
    branches: [main]
jobs:
  trivy-scan:
    steps:
      - name: Run Trivy (filesystem)
        uses: aquasecurity/trivy-action@v1
        with:
          exit-code: "1"
""".strip(),
        encoding="utf-8",
    )

    bad_sentinel = tmp_path / "required-checks-audit.yml"
    bad_sentinel.write_text(
        """
name: required-checks-audit (Sentinel)
on:
  push:
    branches: [main]
  workflow_dispatch:
jobs:
  audit:
    name: required-checks-audit (Sentinel)
    steps:
      - name: Audit required check status
        run: echo "sentinel"
""".strip(),
        encoding="utf-8",
    )

    legacy_failures = {
        finding.rule
        for finding in evaluate_legacy_ci_workflow(load_workflow(bad_legacy_ci))
        if finding.status == "FAIL"
    }
    sentinel_failures = {
        finding.rule
        for finding in evaluate_sentinel_workflow(load_workflow(bad_sentinel))
        if finding.status == "FAIL"
    }

    assert "legacy Trivy reporting mode" in legacy_failures
    assert "legacy Trivy summary step" in legacy_failures
    assert "legacy Trivy summary message" in legacy_failures
    assert "sentinel manual-only trigger" in sentinel_failures
    assert "sentinel audit-only mode marker" in sentinel_failures
    assert "sentinel canonical required context" in sentinel_failures
