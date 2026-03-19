#!/usr/bin/env python3
"""
Read-only CI guardrails drift checker for secret, format, and restore-green
workflow enforcement.

This guard validates the minimal workflow contract that keeps the canonical
PR gate honest:
- `.github/workflows/gitleaks.yml` must run on PRs to `main` and fail closed.
- `.github/workflows/ci.yml` must still enforce Ruff + Black in the required
  `ci` job.
- `.github/workflows/ci.yaml` must keep Trivy in reporting-only mode so the
  legacy pipeline does not regress into deterministic red noise.
- `.github/workflows/required-checks-audit.yml` must stay manual-only and
  audit-only, instead of reintroducing routine auto-run failures.

Exit codes:
- 0: no drift
- 2: drift detected
- 1: execution error
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore[assignment]


DEFAULT_CI_WORKFLOW = Path(".github/workflows/ci.yml")
DEFAULT_GITLEAKS_WORKFLOW = Path(".github/workflows/gitleaks.yml")
DEFAULT_LEGACY_CI_WORKFLOW = Path(".github/workflows/ci.yaml")
DEFAULT_E2E_WORKFLOW = Path(".github/workflows/e2e.yml")
DEFAULT_E2E_TESTS_WORKFLOW = Path(".github/workflows/e2e-tests.yml")
DEFAULT_SHADOW_SOAK_WORKFLOW = Path(".github/workflows/shadow-soak-evidence.yml")
DEFAULT_SENTINEL_WORKFLOW = Path(".github/workflows/required-checks-audit.yml")
DEFAULT_REPORT = Path("reports/CI_GUARDRAILS_DRIFT_REPORT_main.md")
REQUIRED_E2E_SECRETS = [
    "SMTP_FROM",
    "SMTP_HOST",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "ALERT_EMAIL_TO",
    "MEXC_API_KEY",
    "MEXC_API_SECRET",
    "REDIS_PASSWORD",
    "POSTGRES_PASSWORD",
    "GRAFANA_PASSWORD",
]
REQUIRED_SECRET_ENVS = [
    "REDIS_PASSWORD_SECRET",
    "POSTGRES_PASSWORD_SECRET",
    "GRAFANA_PASSWORD_SECRET",
    "SMTP_FROM_SECRET",
    "SMTP_HOST_SECRET",
    "SMTP_USER_SECRET",
    "SMTP_PASSWORD_SECRET",
    "ALERT_EMAIL_TO_SECRET",
    "MEXC_API_KEY_SECRET",
    "MEXC_API_SECRET_SECRET",
]
FORBIDDEN_INLINE_FALLBACKS = [
    "secrets.REDIS_PASSWORD != '' && secrets.REDIS_PASSWORD || 'ci-redis-password'",
    "secrets.POSTGRES_PASSWORD != '' && secrets.POSTGRES_PASSWORD || 'ci-postgres-password'",
    "secrets.GRAFANA_PASSWORD != '' && secrets.GRAFANA_PASSWORD || 'ci-grafana-password'",
]
EXPECTED_PROTECTED_STUB_IF = (
    "steps.preflight.outputs.protected_context == 'true' && "
    "steps.preflight.outputs.e2e_mode == 'STUB'"
)
EXPECTED_NON_PROTECTED_STUB_IF = (
    "steps.preflight.outputs.protected_context != 'true' && "
    "steps.preflight.outputs.e2e_mode == 'STUB'"
)


@dataclass(frozen=True)
class Finding:
    component: str
    rule: str
    status: str
    detail: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only drift check for CI secret/format guardrails."
    )
    parser.add_argument(
        "--ci-workflow",
        default=str(DEFAULT_CI_WORKFLOW),
        help="path to the canonical CI workflow",
    )
    parser.add_argument(
        "--gitleaks-workflow",
        default=str(DEFAULT_GITLEAKS_WORKFLOW),
        help="path to the dedicated gitleaks workflow",
    )
    parser.add_argument(
        "--legacy-ci-workflow",
        default=str(DEFAULT_LEGACY_CI_WORKFLOW),
        help="path to the legacy CI/CD pipeline workflow",
    )
    parser.add_argument(
        "--e2e-workflow",
        default=str(DEFAULT_E2E_WORKFLOW),
        help="path to the canonical E2E smoke workflow",
    )
    parser.add_argument(
        "--e2e-tests-workflow",
        default=str(DEFAULT_E2E_TESTS_WORKFLOW),
        help="path to the paper-trading E2E workflow",
    )
    parser.add_argument(
        "--shadow-soak-workflow",
        default=str(DEFAULT_SHADOW_SOAK_WORKFLOW),
        help="path to the shadow/soak workflow",
    )
    parser.add_argument(
        "--sentinel-workflow",
        default=str(DEFAULT_SENTINEL_WORKFLOW),
        help="path to the manual required-checks-audit workflow",
    )
    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT),
        help="markdown drift report output path",
    )
    return parser.parse_args()


def load_workflow(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Workflow file not found: {path}")

    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Workflow YAML must be a mapping: {path}")
    return payload


def workflow_triggers(payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload.get("on")
    if isinstance(raw, dict):
        return raw

    raw = payload.get(True)
    if isinstance(raw, dict):
        return raw

    return {}


def trigger_branches(payload: dict[str, Any], event_name: str) -> list[str]:
    triggers = workflow_triggers(payload)
    event_cfg = triggers.get(event_name)

    if event_cfg is None:
        return []
    if isinstance(event_cfg, list):
        return []
    if isinstance(event_cfg, dict):
        branches = event_cfg.get("branches")
        if isinstance(branches, list):
            return [str(branch).strip() for branch in branches if str(branch).strip()]
    return []


def find_step(steps: list[Any], name: str) -> dict[str, Any] | None:
    for step in steps:
        if not isinstance(step, dict):
            continue
        step_name = step.get("name")
        if isinstance(step_name, str) and step_name.strip() == name:
            return step
    return None


def normalize_space(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())


def first_job(payload: dict[str, Any]) -> dict[str, Any] | None:
    jobs = payload.get("jobs")
    if not isinstance(jobs, dict):
        return None
    for job in jobs.values():
        if isinstance(job, dict):
            return job
    return None


def contains_use(steps: list[Any], prefix: str) -> dict[str, Any] | None:
    for step in steps:
        if not isinstance(step, dict):
            continue
        uses = step.get("uses")
        if isinstance(uses, str) and uses.startswith(prefix):
            return step
    return None


def record(
    findings: list[Finding], component: str, rule: str, ok: bool, detail: str
) -> None:
    findings.append(
        Finding(
            component=component,
            rule=rule,
            status="PASS" if ok else "FAIL",
            detail=detail,
        )
    )


def evaluate_gitleaks_workflow(payload: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    component = ".github/workflows/gitleaks.yml"

    pr_branches = trigger_branches(payload, "pull_request")
    record(
        findings,
        component,
        "pull_request branch scope",
        "main" in pr_branches,
        f"pull_request branches={pr_branches or 'missing'}",
    )

    push_branches = trigger_branches(payload, "push")
    record(
        findings,
        component,
        "push branch scope",
        "main" in push_branches,
        f"push branches={push_branches or 'missing'}",
    )

    jobs = payload.get("jobs")
    if not isinstance(jobs, dict):
        return findings + [
            Finding(component, "gitleaks job", "FAIL", "jobs mapping missing"),
        ]

    job = jobs.get("gitleaks")
    if not isinstance(job, dict):
        return findings + [
            Finding(component, "gitleaks job", "FAIL", "jobs.gitleaks missing"),
        ]

    job_name = job.get("name")
    record(
        findings,
        component,
        "gitleaks job name",
        job_name == "gitleaks (Secrets-Alarm)",
        f"name={job_name!r}",
    )

    continue_on_error = bool(job.get("continue-on-error", False))
    record(
        findings,
        component,
        "fail-closed job behavior",
        not continue_on_error,
        f"continue-on-error={continue_on_error}",
    )

    steps = job.get("steps")
    if not isinstance(steps, list):
        return findings + [
            Finding(component, "gitleaks steps", "FAIL", "jobs.gitleaks.steps missing"),
        ]

    checkout_step = contains_use(steps, "actions/checkout@")
    checkout_with = (
        checkout_step.get("with", {}) if isinstance(checkout_step, dict) else {}
    )
    fetch_depth = (
        checkout_with.get("fetch-depth") if isinstance(checkout_with, dict) else None
    )
    record(
        findings,
        component,
        "full-history checkout",
        fetch_depth == 0,
        f"fetch-depth={fetch_depth!r}",
    )

    gitleaks_step = contains_use(steps, "gitleaks/gitleaks-action@")
    record(
        findings,
        component,
        "gitleaks action step",
        gitleaks_step is not None,
        (
            "gitleaks/gitleaks-action present"
            if gitleaks_step is not None
            else "gitleaks/gitleaks-action missing"
        ),
    )

    env = gitleaks_step.get("env", {}) if isinstance(gitleaks_step, dict) else {}
    config_value = env.get("GITLEAKS_CONFIG") if isinstance(env, dict) else None
    record(
        findings,
        component,
        "repo gitleaks config",
        config_value == "gitleaks.toml",
        f"GITLEAKS_CONFIG={config_value!r}",
    )

    return findings


def evaluate_ci_workflow(payload: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    component = ".github/workflows/ci.yml"

    jobs = payload.get("jobs")
    if not isinstance(jobs, dict):
        return [Finding(component, "ci job", "FAIL", "jobs mapping missing")]

    job = jobs.get("ci")
    if not isinstance(job, dict):
        return [Finding(component, "ci job", "FAIL", "jobs.ci missing")]

    steps = job.get("steps")
    if not isinstance(steps, list):
        return [Finding(component, "ci steps", "FAIL", "jobs.ci.steps missing")]

    ruff_step = find_step(steps, "Ruff")
    ruff_run = ruff_step.get("run", "") if isinstance(ruff_step, dict) else ""
    record(
        findings,
        component,
        "Ruff step present",
        isinstance(ruff_step, dict),
        "step 'Ruff' present" if isinstance(ruff_step, dict) else "step 'Ruff' missing",
    )
    record(
        findings,
        component,
        "Ruff command",
        isinstance(ruff_run, str) and "ruff check ." in ruff_run,
        f"run snippet={ruff_run!r}",
    )

    black_step = find_step(steps, "Black")
    black_run = black_step.get("run", "") if isinstance(black_step, dict) else ""
    record(
        findings,
        component,
        "Black step present",
        isinstance(black_step, dict),
        (
            "step 'Black' present"
            if isinstance(black_step, dict)
            else "step 'Black' missing"
        ),
    )
    record(
        findings,
        component,
        "Black command",
        isinstance(black_run, str)
        and "black --config pyproject.toml --check" in black_run,
        f"run snippet={black_run!r}",
    )

    return findings


def evaluate_legacy_ci_workflow(payload: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    component = ".github/workflows/ci.yaml"

    push_branches = trigger_branches(payload, "push")
    record(
        findings,
        component,
        "legacy push branch scope",
        "main" in push_branches,
        f"push branches={push_branches or 'missing'}",
    )

    jobs = payload.get("jobs")
    if not isinstance(jobs, dict):
        return findings + [
            Finding(component, "legacy ci jobs", "FAIL", "jobs mapping missing"),
        ]

    trivy_job = jobs.get("trivy-scan")
    if not isinstance(trivy_job, dict):
        return findings + [
            Finding(component, "legacy trivy job", "FAIL", "jobs.trivy-scan missing"),
        ]

    steps = trivy_job.get("steps")
    if not isinstance(steps, list):
        return findings + [
            Finding(component, "legacy trivy steps", "FAIL", "steps missing"),
        ]

    trivy_step = find_step(steps, "Run Trivy (filesystem)")
    trivy_with = trivy_step.get("with", {}) if isinstance(trivy_step, dict) else {}
    exit_code = trivy_with.get("exit-code") if isinstance(trivy_with, dict) else None
    record(
        findings,
        component,
        "legacy Trivy reporting mode",
        exit_code == "0",
        f"exit-code={exit_code!r}",
    )

    summary_step = find_step(steps, "Trivy reporting mode summary")
    summary_run = summary_step.get("run", "") if isinstance(summary_step, dict) else ""
    record(
        findings,
        component,
        "legacy Trivy summary step",
        isinstance(summary_step, dict),
        (
            "step 'Trivy reporting mode summary' present"
            if isinstance(summary_step, dict)
            else "step 'Trivy reporting mode summary' missing"
        ),
    )
    record(
        findings,
        component,
        "legacy Trivy summary message",
        "Non-blocking mode (reporting-only)." in summary_run,
        f"run snippet={summary_run!r}",
    )

    return findings


def evaluate_e2e_workflow(
    payload: dict[str, Any], workflow_path: str, create_step_name: str
) -> list[Finding]:
    findings: list[Finding] = []
    component = workflow_path

    job = first_job(payload)
    if not isinstance(job, dict):
        return [Finding(component, "workflow job", "FAIL", "jobs mapping missing")]

    steps = job.get("steps")
    if not isinstance(steps, list):
        return [Finding(component, "workflow steps", "FAIL", "steps missing")]

    preflight_step = find_step(steps, "Preflight required secrets (REAL vs STUB)")
    preflight_env = (
        preflight_step.get("env", {}) if isinstance(preflight_step, dict) else {}
    )
    preflight_run = (
        preflight_step.get("run", "") if isinstance(preflight_step, dict) else ""
    )
    missing_preflight_envs = [
        secret for secret in REQUIRED_E2E_SECRETS if secret not in preflight_env
    ]
    missing_preflight_required = [
        secret
        for secret in REQUIRED_E2E_SECRETS
        if secret not in normalize_space(preflight_run)
    ]
    record(
        findings,
        component,
        "preflight step present",
        isinstance(preflight_step, dict),
        (
            "step 'Preflight required secrets (REAL vs STUB)' present"
            if isinstance(preflight_step, dict)
            else "step 'Preflight required secrets (REAL vs STUB)' missing"
        ),
    )
    record(
        findings,
        component,
        "preflight secret env mapping",
        not missing_preflight_envs,
        (
            "all required E2E secrets mapped in preflight env"
            if not missing_preflight_envs
            else f"missing env keys={missing_preflight_envs}"
        ),
    )
    record(
        findings,
        component,
        "preflight required secret list",
        not missing_preflight_required,
        (
            "preflight required list contains all expected secrets"
            if not missing_preflight_required
            else f"missing from required list={missing_preflight_required}"
        ),
    )

    fail_step = find_step(steps, "Fail closed on protected STUB mode")
    fail_if = (
        normalize_space(fail_step.get("if")) if isinstance(fail_step, dict) else ""
    )
    fail_run = fail_step.get("run", "") if isinstance(fail_step, dict) else ""
    record(
        findings,
        component,
        "protected STUB hard fail step",
        isinstance(fail_step, dict),
        (
            "protected STUB hard fail step present"
            if isinstance(fail_step, dict)
            else "step 'Fail closed on protected STUB mode' missing"
        ),
    )
    record(
        findings,
        component,
        "protected STUB hard fail condition",
        fail_if == normalize_space(EXPECTED_PROTECTED_STUB_IF),
        f"if={fail_if!r}",
    )
    record(
        findings,
        component,
        "protected STUB hard fail message",
        "Protected run cannot use STUB MODE. Missing secrets:" in fail_run,
        f"run snippet={fail_run!r}",
    )

    stub_step = find_step(steps, "Mark non-protected STUB mode")
    stub_if = (
        normalize_space(stub_step.get("if")) if isinstance(stub_step, dict) else ""
    )
    stub_run = stub_step.get("run", "") if isinstance(stub_step, dict) else ""
    record(
        findings,
        component,
        "non-protected STUB visibility step",
        isinstance(stub_step, dict),
        (
            "step 'Mark non-protected STUB mode' present"
            if isinstance(stub_step, dict)
            else "step 'Mark non-protected STUB mode' missing"
        ),
    )
    record(
        findings,
        component,
        "non-protected STUB visibility condition",
        stub_if == normalize_space(EXPECTED_NON_PROTECTED_STUB_IF),
        f"if={stub_if!r}",
    )
    record(
        findings,
        component,
        "non-protected STUB summary message",
        "NON-BLOCKING / STUB ONLY" in stub_run,
        f"run snippet={stub_run!r}",
    )

    create_step = find_step(steps, create_step_name)
    create_env = create_step.get("env", {}) if isinstance(create_step, dict) else {}
    create_run = create_step.get("run", "") if isinstance(create_step, dict) else ""
    missing_create_envs = [
        secret_env
        for secret_env in REQUIRED_SECRET_ENVS
        if secret_env not in create_env
    ]
    fallback_hits = [
        snippet for snippet in FORBIDDEN_INLINE_FALLBACKS if snippet in create_run
    ]
    record(
        findings,
        component,
        "create secrets step present",
        isinstance(create_step, dict),
        (
            f"step '{create_step_name}' present"
            if isinstance(create_step, dict)
            else f"step '{create_step_name}' missing"
        ),
    )
    record(
        findings,
        component,
        "create secrets env mapping",
        not missing_create_envs,
        (
            "all required secret envs mapped for materialization"
            if not missing_create_envs
            else f"missing env keys={missing_create_envs}"
        ),
    )
    record(
        findings,
        component,
        "forbidden inline secret fallbacks",
        not fallback_hits,
        (
            "no inline secret fallback expressions found"
            if not fallback_hits
            else f"forbidden fallback snippets present={fallback_hits}"
        ),
    )
    record(
        findings,
        component,
        "explicit STUB placeholder materialization",
        all(
            placeholder in create_run
            for placeholder in (
                'REDIS_VAL="ci-redis-password"',
                'POSTGRES_VAL="ci-postgres-password"',
                'GRAFANA_VAL="ci-grafana-password"',
            )
        )
        and 'if [[ "${{ steps.preflight.outputs.e2e_mode }}" == "STUB" ]]'
        in create_run,
        "STUB placeholders for stack secrets remain explicit and mode-bound",
    )
    record(
        findings,
        component,
        "REAL materialization guard",
        "REAL mode missing required secrets during materialization:" in create_run,
        (
            "REAL materialization guard present"
            if "REAL mode missing required secrets during materialization:"
            in create_run
            else "REAL materialization guard missing"
        ),
    )

    return findings


def evaluate_sentinel_workflow(payload: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    component = ".github/workflows/required-checks-audit.yml"

    triggers = workflow_triggers(payload)
    trigger_keys = {str(key) for key in triggers.keys()}
    record(
        findings,
        component,
        "sentinel manual-only trigger",
        trigger_keys == {"workflow_dispatch"},
        f"trigger keys={sorted(trigger_keys) or 'missing'}",
    )

    jobs = payload.get("jobs")
    if not isinstance(jobs, dict):
        return findings + [
            Finding(component, "sentinel jobs", "FAIL", "jobs mapping missing"),
        ]

    job = jobs.get("audit")
    if not isinstance(job, dict):
        return findings + [
            Finding(component, "sentinel audit job", "FAIL", "jobs.audit missing"),
        ]

    job_name = job.get("name")
    record(
        findings,
        component,
        "sentinel job name",
        job_name == "required-checks-audit (Sentinel)",
        f"name={job_name!r}",
    )

    steps = job.get("steps")
    if not isinstance(steps, list):
        return findings + [
            Finding(component, "sentinel steps", "FAIL", "steps missing"),
        ]

    audit_step = find_step(steps, "Audit required check status")
    audit_run = audit_step.get("run", "") if isinstance(audit_step, dict) else ""
    record(
        findings,
        component,
        "sentinel audit step present",
        isinstance(audit_step, dict),
        (
            "step 'Audit required check status' present"
            if isinstance(audit_step, dict)
            else "step 'Audit required check status' missing"
        ),
    )
    record(
        findings,
        component,
        "sentinel audit-only mode marker",
        "Sentinel mode: audit-only" in audit_run and "always exits 0." in audit_run,
        "audit-only marker and exit-0 summary must stay explicit",
    )
    record(
        findings,
        component,
        "sentinel canonical required context",
        "ci (Unit/Integration + Lint gesammelt)" in audit_run,
        "canonical required context must stay listed in required_checks",
    )

    return findings


def timestamps() -> tuple[str, str]:
    now_utc = datetime.now(timezone.utc)
    utc_text = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    if ZoneInfo is None:
        berlin_text = utc_text
    else:
        berlin_text = now_utc.astimezone(ZoneInfo("Europe/Berlin")).strftime(
            "%Y-%m-%dT%H:%M:%S%z"
        )
        berlin_text = f"{berlin_text[:-2]}:{berlin_text[-2:]}"
    return berlin_text, utc_text


def write_report(report_path: Path, findings: list[Finding]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    berlin_ts, utc_ts = timestamps()
    failures = [finding for finding in findings if finding.status == "FAIL"]
    state = "DRIFT DETECTED" if failures else "NO DRIFT"

    table_lines = [
        "| component | rule | status | detail |",
        "|---|---|---|---|",
    ]
    for finding in findings:
        detail = finding.detail.replace("|", "\\|")
        table_lines.append(
            f"| `{finding.component}` | `{finding.rule}` | `{finding.status}` | {detail} |"
        )

    failed_rules = (
        "\n".join(
            f"- `{finding.component}` -> `{finding.rule}`: {finding.detail}"
            for finding in failures
        )
        if failures
        else "- none"
    )

    report = f"""# CI Guardrails Drift Report (main)

Timestamp (Europe/Berlin): `{berlin_ts}`  
Timestamp (UTC): `{utc_ts}`  
State: **{state}**

## Scope

- Secret guardrail workflow: `.github/workflows/gitleaks.yml`
- Format guardrail workflow: `.github/workflows/ci.yml`
- Legacy restore-green guardrails:
  - `.github/workflows/ci.yaml`
  - `.github/workflows/required-checks-audit.yml`
- E2E protected-context guardrails:
  - `.github/workflows/e2e.yml`
  - `.github/workflows/e2e-tests.yml`
  - `.github/workflows/shadow-soak-evidence.yml`
- Mode: read-only contract validation

## Failed Rules

{failed_rules}

## Findings

{chr(10).join(table_lines)}

## What To Do

- If drift is unintended, restore the missing secret/format/restore-green/E2E guard in the workflow file.
- If drift is intended, update this checker in the same reviewed PR so the contract stays explicit.
"""
    report_path.write_text(report, encoding="utf-8")


def main() -> int:
    args = parse_args()

    ci_payload = load_workflow(Path(args.ci_workflow))
    gitleaks_payload = load_workflow(Path(args.gitleaks_workflow))
    legacy_ci_payload = load_workflow(Path(args.legacy_ci_workflow))
    e2e_payload = load_workflow(Path(args.e2e_workflow))
    e2e_tests_payload = load_workflow(Path(args.e2e_tests_workflow))
    shadow_soak_payload = load_workflow(Path(args.shadow_soak_workflow))
    sentinel_payload = load_workflow(Path(args.sentinel_workflow))

    findings = evaluate_gitleaks_workflow(gitleaks_payload)
    findings.extend(evaluate_ci_workflow(ci_payload))
    findings.extend(evaluate_legacy_ci_workflow(legacy_ci_payload))
    findings.extend(evaluate_sentinel_workflow(sentinel_payload))
    findings.extend(
        evaluate_e2e_workflow(
            e2e_payload,
            ".github/workflows/e2e.yml",
            "Create CI secrets directory",
        )
    )
    findings.extend(
        evaluate_e2e_workflow(
            e2e_tests_payload,
            ".github/workflows/e2e-tests.yml",
            "Create CI Secrets Directory",
        )
    )
    findings.extend(
        evaluate_e2e_workflow(
            shadow_soak_payload,
            ".github/workflows/shadow-soak-evidence.yml",
            "Create CI secrets",
        )
    )

    report_path = Path(args.report)
    write_report(report_path, findings)

    failures = [finding for finding in findings if finding.status == "FAIL"]
    print(
        "CI guardrails: {total} checks, {failed} failures".format(
            total=len(findings),
            failed=len(failures),
        )
    )
    print(f"Drift report: {report_path.as_posix()}")

    if failures:
        return 2
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1) from exc
