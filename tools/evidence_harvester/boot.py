from __future__ import annotations

import argparse
import importlib
import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from core.utils.clock import utcnow as cdb_utcnow

BOOT_READINESS_SCHEMA = "cdb.evidence_harvester.boot_readiness.v1"

ALWAYS_ALLOWED_MODES: tuple[str, ...] = ("status", "preflight")
INSTALL_PLAN_MODES: tuple[str, ...] = ("install-plan",)
PASS_THROUGH_MODES: tuple[str, ...] = ("render-operator-handoff",)

SAFETY_BANNER = (
    "Default mode is status-only. "
    "No Docker/runtime/DB/secrets/network action. "
    "No LR-Go, no Live-Go, no Echtgeld-Go."
)

HARVESTER_MODULES: tuple[str, ...] = (
    "tools.evidence_harvester.runner",
    "tools.evidence_harvester.watchdog",
    "tools.evidence_harvester.write_audit",
    "tools.evidence_harvester.collector",
    "tools.evidence_harvester.snapshot",
    "tools.evidence_harvester.alerts",
    "tools.evidence_harvester.scheduler",
    "tools.evidence_harvester.validation",
)

HARVESTER_ARTIFACT_DIRS: tuple[str, ...] = (
    "artifacts/evidence_harvester/runner",
    "artifacts/evidence_harvester/scheduled",
    "artifacts/evidence_harvester/watchdog",
    "artifacts/evidence_harvester/write_audit",
)

EXPECTED_SCRIPTS: tuple[str, ...] = ("scripts/evidence_harvester_task.ps1",)


class BootReadinessError(ValueError):
    pass


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _format_ts(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _now_utc() -> datetime:
    now = cdb_utcnow()
    if now.tzinfo is None:
        return now.replace(tzinfo=UTC)
    return now.astimezone(UTC)


def _format_json(payload: Mapping[str, Any], pretty: bool) -> str:
    return json.dumps(
        payload,
        indent=2 if pretty else None,
        sort_keys=True,
        ensure_ascii=True,
    )


def _emit(payload: Mapping[str, Any], pretty: bool) -> None:
    print(_format_json(payload, pretty))


def _write_text(path: Path, text: str) -> None:
    path.write_text(text + ("" if text.endswith("\n") else "\n"), encoding="utf-8")


@dataclass(frozen=True, slots=True)
class BootReadinessFinding:
    check_id: str
    check_name: str
    severity: str
    message: str
    artifact: str = ""
    field_name: str = ""


@dataclass(frozen=True, slots=True)
class BootReadinessVerdict:
    verdict: str
    total_checks: int
    pass_count: int
    warn_count: int
    fail_count: int


@dataclass(frozen=True, slots=True)
class BootReadinessReport:
    schema_version: str
    evaluated_at_utc: str
    mode: str
    repo_root_valid: bool
    harvester_modules_importable: bool
    artifact_dirs_available: bool
    scheduler_script_present: bool
    command_plan_available: bool
    docker_available: bool
    safety_boundaries_ok: bool
    verdict: BootReadinessVerdict
    findings: tuple[BootReadinessFinding, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _check_repo_root(repo_root: Path) -> list[BootReadinessFinding]:
    findings: list[BootReadinessFinding] = []
    if not repo_root.exists():
        findings.append(
            BootReadinessFinding(
                check_id="B001",
                check_name="Repo root exists",
                severity="fail",
                message=f"Repo root does not exist: {repo_root}",
            )
        )
        return findings

    git_dir = repo_root / ".git"
    if not git_dir.exists():
        findings.append(
            BootReadinessFinding(
                check_id="B001",
                check_name="Repo root .git",
                severity="warn",
                message=f".git directory not found at {git_dir}",
            )
        )
    else:
        findings.append(
            BootReadinessFinding(
                check_id="B001",
                check_name="Repo root valid",
                severity="pass",
                message=f"Repo root resolved: {repo_root}",
            )
        )
    return findings


def _check_harvester_modules(
    repo_root: Path,
) -> list[BootReadinessFinding]:
    findings: list[BootReadinessFinding] = []
    sys.path.insert(0, str(repo_root))
    all_importable = True
    for mod_name in HARVESTER_MODULES:
        try:
            importlib.import_module(mod_name)
            findings.append(
                BootReadinessFinding(
                    check_id="B002",
                    check_name=f"Module importable: {mod_name}",
                    severity="pass",
                    message=f"{mod_name} imported successfully",
                    artifact=mod_name,
                )
            )
        except ImportError as exc:
            all_importable = False
            findings.append(
                BootReadinessFinding(
                    check_id="B002",
                    check_name=f"Module importable: {mod_name}",
                    severity="fail",
                    message=f"Cannot import {mod_name}: {exc}",
                    artifact=mod_name,
                )
            )
    if all_importable and len(HARVESTER_MODULES) > 0:
        findings.append(
            BootReadinessFinding(
                check_id="B002",
                check_name="All harvester modules importable",
                severity="pass",
                message=f"All {len(HARVESTER_MODULES)} harvester modules importable",
            )
        )
    return findings


def _check_artifact_dirs(
    repo_root: Path,
) -> list[BootReadinessFinding]:
    findings: list[BootReadinessFinding] = []
    all_available = True
    for rel_path in HARVESTER_ARTIFACT_DIRS:
        resolved = (repo_root / rel_path).resolve()
        if resolved.exists():
            findings.append(
                BootReadinessFinding(
                    check_id="B003",
                    check_name=f"Artifact dir exists: {rel_path}",
                    severity="pass",
                    message=f"Directory exists: {resolved}",
                    artifact=rel_path,
                )
            )
        else:
            try:
                resolved.mkdir(parents=True, exist_ok=True)
                findings.append(
                    BootReadinessFinding(
                        check_id="B003",
                        check_name=f"Artifact dir creatable: {rel_path}",
                        severity="warn",
                        message=f"Directory created: {resolved}",
                        artifact=rel_path,
                    )
                )
            except OSError as exc:
                all_available = False
                findings.append(
                    BootReadinessFinding(
                        check_id="B003",
                        check_name=f"Artifact dir not creatable: {rel_path}",
                        severity="fail",
                        message=f"Cannot create {rel_path}: {exc}",
                        artifact=rel_path,
                    )
                )
    if all_available:
        findings.append(
            BootReadinessFinding(
                check_id="B003",
                check_name="Artifact directories available",
                severity="pass",
                message="All required artifact directories exist or are creatable",
            )
        )
    return findings


def _check_scheduler_script(
    repo_root: Path,
) -> list[BootReadinessFinding]:
    findings: list[BootReadinessFinding] = []
    all_present = True
    for rel_path in EXPECTED_SCRIPTS:
        resolved = (repo_root / rel_path).resolve()
        if resolved.exists():
            findings.append(
                BootReadinessFinding(
                    check_id="B004",
                    check_name=f"Scheduler script present: {rel_path}",
                    severity="pass",
                    message=f"Script found: {resolved}",
                    artifact=rel_path,
                )
            )
        else:
            all_present = False
            findings.append(
                BootReadinessFinding(
                    check_id="B004",
                    check_name=f"Scheduler script missing: {rel_path}",
                    severity="warn",
                    message=f"Script not found: {resolved}. Install via #3733 / Operator Runtime-GO.",
                    artifact=rel_path,
                )
            )
    if all_present and len(EXPECTED_SCRIPTS) > 0:
        findings.append(
            BootReadinessFinding(
                check_id="B004",
                check_name="All scheduler scripts present",
                severity="pass",
                message="All expected scheduler scripts found",
            )
        )
    return findings


def _check_docker_readiness() -> list[BootReadinessFinding]:
    findings: list[BootReadinessFinding] = []
    import shutil

    docker_path = shutil.which("docker")
    if docker_path:
        findings.append(
            BootReadinessFinding(
                check_id="B005",
                check_name="Docker available",
                severity="pass",
                message=f"Docker found at {docker_path}. Not started — no mutation performed.",
                artifact=docker_path,
            )
        )
    else:
        findings.append(
            BootReadinessFinding(
                check_id="B005",
                check_name="Docker available",
                severity="warn",
                message="Docker not found on PATH. Not required for fixture mode.",
            )
        )
    return findings


def _check_safety_boundaries() -> list[BootReadinessFinding]:
    findings: list[BootReadinessFinding] = []
    all_ok = True

    for mod_key, expected_banner in [
        ("runner", "no LR-Go, no Live-Go, no Echtgeld-Go"),
    ]:
        try:
            mod = importlib.import_module(f"tools.evidence_harvester.{mod_key}")
            mod_src = getattr(mod, "SAFETY_BANNER", None) or getattr(mod, "__doc__", "")
            if expected_banner.lower() in mod_src.lower():
                findings.append(
                    BootReadinessFinding(
                        check_id="B006",
                        check_name=f"Safety banner in {mod_key}.py",
                        severity="pass",
                        message=f"Safety banner present in {mod_key}.py",
                        artifact=f"tools/evidence_harvester/{mod_key}.py",
                    )
                )
            else:
                findings.append(
                    BootReadinessFinding(
                        check_id="B006",
                        check_name=f"Safety banner in {mod_key}.py",
                        severity="warn",
                        message=(
                            f"Safety banner may be missing in {mod_key}.py. "
                            "Expected: no LR-Go / no Live-Go / no Echtgeld-Go"
                        ),
                        artifact=f"tools/evidence_harvester/{mod_key}.py",
                    )
                )
        except ImportError:
            all_ok = False
            findings.append(
                BootReadinessFinding(
                    check_id="B006",
                    check_name=f"Safety banner check: {mod_key}.py",
                    severity="fail",
                    message=f"Cannot import {mod_key}.py for safety check",
                    artifact=f"tools/evidence_harvester/{mod_key}.py",
                )
            )

    if all_ok:
        findings.append(
            BootReadinessFinding(
                check_id="B006",
                check_name="Safety boundaries ok",
                severity="pass",
                message="Safety boundaries present and enforceable",
            )
        )
    return findings


def _check_command_plan_available() -> list[BootReadinessFinding]:
    findings: list[BootReadinessFinding] = []
    commands = {
        "boot status": ["python", "-m", "tools.evidence_harvester.boot", "status"],
        "boot preflight": [
            "python",
            "-m",
            "tools.evidence_harvester.boot",
            "preflight",
        ],
        "boot install-plan": [
            "python",
            "-m",
            "tools.evidence_harvester.boot",
            "install-plan",
        ],
        "boot render-operator-handoff": [
            "python",
            "-m",
            "tools.evidence_harvester.boot",
            "render-operator-handoff",
        ],
        "runner status": [
            "python",
            "-m",
            "tools.evidence_harvester.runner",
            "status",
        ],
        "scheduler plan": [
            "python",
            "-m",
            "tools.evidence_harvester.scheduler",
            "plan",
        ],
    }
    findings.append(
        BootReadinessFinding(
            check_id="B007",
            check_name="Command plan available",
            severity="pass",
            message=f"{len(commands)} safe commands available. "
            "No Docker/runtime/DB/secrets action implied.",
            artifact=", ".join(sorted(commands.keys())),
        )
    )
    return findings


def _build_findings(
    repo_root: Path,
    mode: str,
) -> list[BootReadinessFinding]:
    all_findings: list[BootReadinessFinding] = []

    if mode in ALWAYS_ALLOWED_MODES + INSTALL_PLAN_MODES + PASS_THROUGH_MODES:
        pass
    else:
        all_findings.append(
            BootReadinessFinding(
                check_id="B000",
                check_name="Mode allowed",
                severity="fail",
                message=f"Unknown mode: {mode}. Allowed: status, preflight, install-plan, render-operator-handoff",
            )
        )
        return all_findings

    all_findings.extend(_check_repo_root(repo_root))
    all_findings.extend(_check_harvester_modules(repo_root))

    if mode in ("install-plan", "render-operator-handoff"):
        pass
    else:
        all_findings.extend(_check_artifact_dirs(repo_root))
        all_findings.extend(_check_scheduler_script(repo_root))
        all_findings.extend(_check_docker_readiness())
        all_findings.extend(_check_safety_boundaries())
        all_findings.extend(_check_command_plan_available())

    return all_findings


def _build_report(
    all_findings: Sequence[BootReadinessFinding],
    repo_root: Path,
    mode: str,
    eval_now: datetime,
) -> BootReadinessReport:
    fail_count = sum(1 for f in all_findings if f.severity == "fail")
    warn_count = sum(1 for f in all_findings if f.severity == "warn")
    pass_count = sum(1 for f in all_findings if f.severity == "pass")

    if fail_count:
        verdict = "FAIL"
    elif warn_count:
        verdict = "WARN"
    else:
        verdict = "PASS"

    repo_root_valid = not any(
        f.check_id == "B001" and f.severity == "fail" for f in all_findings
    )
    harvester_modules_importable = not any(
        f.check_id == "B002" and f.severity == "fail" for f in all_findings
    )
    artifact_dirs_available = not any(
        f.check_id == "B003" and f.severity == "fail" for f in all_findings
    )
    scheduler_script_present = not any(
        f.check_id == "B004" and f.severity == "fail" for f in all_findings
    )
    docker_available = any(
        f.check_id == "B005" and f.severity == "pass" for f in all_findings
    )
    safety_boundaries_ok = not any(
        f.check_id == "B006" and f.severity == "fail" for f in all_findings
    )
    command_plan_available = not any(
        f.check_id == "B007" and f.severity == "fail" for f in all_findings
    )

    sorted_findings = tuple(
        sorted(
            all_findings,
            key=lambda f: (
                {"fail": 0, "warn": 1, "pass": 2}.get(f.severity, 9),
                f.check_id,
            ),
        )
    )

    return BootReadinessReport(
        schema_version=BOOT_READINESS_SCHEMA,
        evaluated_at_utc=_format_ts(eval_now),
        mode=mode,
        repo_root_valid=repo_root_valid,
        harvester_modules_importable=harvester_modules_importable,
        artifact_dirs_available=artifact_dirs_available,
        scheduler_script_present=scheduler_script_present,
        command_plan_available=command_plan_available,
        docker_available=docker_available,
        safety_boundaries_ok=safety_boundaries_ok,
        verdict=BootReadinessVerdict(
            verdict=verdict,
            total_checks=len(sorted_findings),
            pass_count=pass_count,
            warn_count=warn_count,
            fail_count=fail_count,
        ),
        findings=sorted_findings,
    )


def _run_boot_readiness(
    repo_root: Path,
    mode: str,
    now: datetime,
) -> BootReadinessReport:
    findings = _build_findings(repo_root, mode)
    return _build_report(findings, repo_root, mode, now)


def _status(repo_root: Path, now: datetime) -> BootReadinessReport:
    return _run_boot_readiness(repo_root, "status", now)


def _preflight(repo_root: Path, now: datetime) -> BootReadinessReport:
    return _run_boot_readiness(repo_root, "preflight", now)


def _install_plan(repo_root: Path, now: datetime) -> BootReadinessReport:
    report = _run_boot_readiness(repo_root, "install-plan", now)
    return report


def _render_operator_handoff_md(report: BootReadinessReport) -> str:
    payload = report.to_dict()
    lines = [
        "# Evidence Harvester Boot — Operator Handoff",
        "",
        "**This handoff is rendered from boot-readiness state. "
        "No action has been taken. No Docker/runtime/DB/secrets "
        "mutation performed.**",
        "",
        "## Boot Verdict",
        f"- Verdict: **{payload['verdict']['verdict']}**",
        f"- Evaluated at (UTC): `{payload['evaluated_at_utc']}`",
        f"- Mode: `{payload['mode']}`",
        "",
        "## Readiness Flags",
        f"- Repo root valid: `{payload['repo_root_valid']}`",
        f"- Harvester modules importable: `{payload['harvester_modules_importable']}`",
        f"- Artifact dirs available: `{payload['artifact_dirs_available']}`",
        f"- Scheduler script present: `{payload['scheduler_script_present']}`",
        f"- Command plan available: `{payload['command_plan_available']}`",
        f"- Docker available: `{payload['docker_available']}`",
        f"- Safety boundaries ok: `{payload['safety_boundaries_ok']}`",
        "",
        "## Operator Steps to Enable Reboot-Resilient Always-On Mode",
        "",
        "1. **Verify boot readiness** — ensure boot status returns PASS:",
        "",
        "   ```powershell",
        "   python -m tools.evidence_harvester.boot status --pretty",
        "   ```",
        "",
        "2. **Install Windows Task Scheduler** (requires #3733 / Operator Runtime-GO):",
        "",
        "   ```powershell",
        "   python -m tools.evidence_harvester.scheduler install --fixture <path> --explicit",
        "   ```",
        "",
        "3. **Enable Docker-based background runner** (requires separate Docker/infra GO via Infra-Mutation-Gate):",
        "",
        "   - Verify `docker_available` is True in boot readiness.",
        "   - Use `boot install-plan` to see the full command surface before any Docker action.",
        "   - Do not start Docker stack from the boot module — Docker mutation requires explicit",
        "     Infra-Mutation-Gate approval (see #3733 host-resilience tiers doc).",
        "",
        "4. **Verify scheduled task runs**:",
        "",
        "   ```powershell",
        "   python -m tools.evidence_harvester.boot status --pretty",
        "   python -m tools.evidence_harvester.scheduler status --pretty",
        "   ```",
        "",
        "5. **Monitor with watchdog**:",
        "",
        "   ```powershell",
        "   python -m tools.evidence_harvester.watchdog status --pretty",
        "   ```",
        "",
        "## Reboot-Resilience",
        "",
        "After the Windows Task is installed (#3733 / Operator Runtime-GO), the task survives reboots automatically:",
        "- Windows Task Scheduler starts the harvester daily at the configured time.",
        "- The boot module can be run at any time to verify readiness post-reboot.",
        "- If Docker is used instead, a Docker restart policy or Windows scheduled task",
        "  restart is needed — both require explicit Infra-Mutation-Gate approval.",
        "",
        "## Safety",
        "- No LR-Go, no Live-Go, no Echtgeld-Go.",
        "- No Docker, runtime, DB, secrets, or network write action.",
        "- No Windows Task install was performed.",
        "- Boot readiness is read-only; does not modify any files.",
    ]
    return "\n".join(lines) + "\n"


def _render_report_md(report: BootReadinessReport) -> str:
    payload = report.to_dict()
    lines = [
        "# Evidence Harvester Boot Readiness Report",
        "",
        "## Metadata",
        f"- Schema version: `{payload['schema_version']}`",
        f"- Evaluated at (UTC): `{payload['evaluated_at_utc']}`",
        f"- Mode: `{payload['mode']}`",
        "",
        "## Readiness Flags",
        f"- Repo root valid: `{payload['repo_root_valid']}`",
        f"- Harvester modules importable: `{payload['harvester_modules_importable']}`",
        f"- Artifact dirs available: `{payload['artifact_dirs_available']}`",
        f"- Scheduler script present: `{payload['scheduler_script_present']}`",
        f"- Command plan available: `{payload['command_plan_available']}`",
        f"- Docker available: `{payload['docker_available']}`",
        f"- Safety boundaries ok: `{payload['safety_boundaries_ok']}`",
        "",
        "## Summary",
        f"- Verdict: **{payload['verdict']['verdict']}**",
        f"- Total checks: {payload['verdict']['total_checks']}",
        f"- Pass: {payload['verdict']['pass_count']}",
        f"- Warn: {payload['verdict']['warn_count']}",
        f"- Fail: {payload['verdict']['fail_count']}",
        "",
        "## Findings",
    ]
    for item in payload["findings"]:
        icon = {"fail": "FAIL", "warn": "WARN", "pass": "PASS"}.get(
            item["severity"], "????"
        )
        artifact_part = f" [{item['artifact']}]" if item.get("artifact") else ""
        field_part = f" ({item['field_name']})" if item.get("field_name") else ""
        lines.append(
            f"  [{icon}] {item['check_name']}{artifact_part}{field_part}: {item['message']}"
        )
    lines.extend(
        [
            "",
            "## Safety",
            "- No LR-Go / No Live-Go / No Echtgeld-Go.",
            "- No Docker, runtime, DB, secrets, or network write action.",
            "- Boot readiness is read-only; does not modify files or start services.",
            "- Default mode is status-only.",
            "- For Docker/infra mutation, separate Infra-Mutation-Gate approval required.",
        ]
    )
    return "\n".join(lines) + "\n"


def _add_shared_args(parser_obj: argparse.ArgumentParser) -> None:
    parser_obj.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )
    parser_obj.add_argument(
        "--json-output",
        type=Path,
        help="Optional path for boot readiness report JSON.",
    )
    parser_obj.add_argument(
        "--markdown-output",
        type=Path,
        help="Optional path for boot readiness report Markdown.",
    )
    parser_obj.add_argument(
        "--evaluated-at-utc",
        help="Optional explicit timestamp for deterministic tests.",
    )


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    argv = list(argv or [])
    if not argv:
        argv = ["status"]

    parser = argparse.ArgumentParser(
        description="Evidence harvester boot readiness — detect, report, hand off."
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser(
        "status",
        help="Full system readiness assessment.",
    )
    _add_shared_args(status_parser)
    status_parser.set_defaults(handler=lambda ns: _handle_status(ns, _repo_root()))

    preflight_parser = subparsers.add_parser(
        "preflight",
        help="Quick module-import and path check.",
    )
    _add_shared_args(preflight_parser)
    preflight_parser.set_defaults(
        handler=lambda ns: _handle_preflight(ns, _repo_root())
    )

    install_plan_parser = subparsers.add_parser(
        "install-plan",
        help="Produce explicit command plan for Docker/Task setup.",
    )
    _add_shared_args(install_plan_parser)
    install_plan_parser.set_defaults(
        handler=lambda ns: _handle_install_plan(ns, _repo_root())
    )

    handoff_parser = subparsers.add_parser(
        "render-operator-handoff",
        help="Render operator handoff document.",
    )
    _add_shared_args(handoff_parser)
    handoff_parser.set_defaults(handler=lambda ns: _handle_handoff(ns, _repo_root()))

    args = parser.parse_args(argv)
    return args.handler(args)


def _resolve_now(args: argparse.Namespace) -> datetime:
    if args.evaluated_at_utc:
        return _parse_ts(args.evaluated_at_utc, "--evaluated-at-utc")
    return _now_utc()


def _parse_ts(value: str, field_name: str) -> datetime:
    text = value.strip()
    if not text:
        raise BootReadinessError(f"{field_name} must not be blank")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise BootReadinessError(
            f"{field_name} must be an ISO-8601 UTC timestamp"
        ) from exc
    if parsed.tzinfo is None:
        raise BootReadinessError(f"{field_name} must be timezone-aware UTC")
    return parsed.astimezone(UTC)


def _handle_status(args: argparse.Namespace, repo_root: Path) -> int:
    now = _resolve_now(args)
    report = _status(repo_root, now)
    _emit_report(args, report)
    return 0 if report.verdict.verdict != "FAIL" else 1


def _handle_preflight(args: argparse.Namespace, repo_root: Path) -> int:
    now = _resolve_now(args)
    report = _preflight(repo_root, now)
    _emit_report(args, report)
    return 0 if report.verdict.verdict != "FAIL" else 1


def _handle_install_plan(args: argparse.Namespace, repo_root: Path) -> int:
    now = _resolve_now(args)
    report = _install_plan(repo_root, now)
    plan_payload = _build_install_plan_payload(report, args.pretty)
    _emit(plan_payload, args.pretty)
    _write_report_files(args, report)
    return 0 if report.verdict.verdict != "FAIL" else 1


def _build_install_plan_payload(
    report: BootReadinessReport, pretty: bool
) -> dict[str, Any]:
    return {
        "mode": "install-plan",
        "default_mode": "dry-run",
        "plan_only": True,
        "boot_readiness": {
            "schema_version": report.schema_version,
            "evaluated_at_utc": report.evaluated_at_utc,
            "verdict": report.verdict.verdict,
            "repo_root_valid": report.repo_root_valid,
            "harvester_modules_importable": report.harvester_modules_importable,
            "artifact_dirs_available": report.artifact_dirs_available,
            "scheduler_script_present": report.scheduler_script_present,
            "docker_available": report.docker_available,
            "safety_boundaries_ok": report.safety_boundaries_ok,
        },
        "available_steps": [
            {
                "step": "verify-boot-readiness",
                "command": "python -m tools.evidence_harvester.boot status --pretty",
            },
            {
                "step": "install-windows-task",
                "command": "python -m tools.evidence_harvester.scheduler install --fixture <path> --explicit",
                "requires_go": "#3733 Operator Runtime-GO",
            },
            {
                "step": "start-docker-stack",
                "command": "docker compose -f infrastructure/compose/compose.blue.yml up -d",
                "requires_go": "separate Infra-Mutation-Gate approval",
            },
        ],
        "safety": [
            "Plan-only. No action taken.",
            "No Docker/runtime/DB/secrets mutation.",
            "Each step requires its own GO gate (#3733 Operator Runtime-GO, Infra-Mutation-Gate).",
            "No LR-Go / No Live-Go / No Echtgeld-Go.",
        ],
    }


def _handle_handoff(args: argparse.Namespace, repo_root: Path) -> int:
    now = _resolve_now(args)
    report = _status(repo_root, now)
    handoff = _render_operator_handoff_md(report)
    print(handoff)
    _write_report_files(args, report)
    return 0 if report.verdict.verdict != "FAIL" else 1


def _emit_report(args: argparse.Namespace, report: BootReadinessReport) -> None:
    payload = report.to_dict()
    json_text = json.dumps(
        payload,
        indent=2 if args.pretty else None,
        sort_keys=True,
        ensure_ascii=True,
    )
    print(json_text)

    _write_report_files(args, report, json_text)


def _write_report_files(
    args: argparse.Namespace, report: BootReadinessReport, json_text: str = ""
) -> None:
    if not json_text:
        json_text = json.dumps(
            report.to_dict(),
            indent=2 if args.pretty else None,
            sort_keys=True,
            ensure_ascii=True,
        )
    if args.json_output:
        _write_text(args.json_output, json_text)
    if args.markdown_output:
        _write_text(args.markdown_output, _render_report_md(report))


if __name__ == "__main__":
    import sys as _sys

    _sys.exit(main())
