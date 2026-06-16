"""Read-only developer onboarding doctor for CDB.

Validates local developer setup without dangerous actions,
secret output, stack mutation, DB writes, or MCP mutations.

Usage:
    python -m tools.onboarding_doctor
    python -m tools.onboarding_doctor --format json
    python -m tools.onboarding_doctor --report docs/evidence/local_onboarding_check.md
    ./tools/cdb.ps1 onboarding doctor
    ./tools/cdb.ps1 onboarding doctor --report docs/evidence/local_onboarding_check.md
    make onboarding-doctor

Exit codes:
    0 - all checks PASS or only non-blocking WARN
    1 - one or more FAIL checks (onboarding not usable)
    2 - CLI usage error

Issue: #3232
Parent: #3226
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from core.utils.clock import utcnow as cdb_utcnow  # noqa: E402

CheckResult = str  # "PASS" | "WARN" | "FAIL" | "SKIP"
EnvVarCheck = str  # "set" | "unset" | "invalid"


ONBOARDING_FILE_CHECKS: list[str] = [
    "README.md",
    "docs/index.md",
    "DEVELOPER_ONBOARDING.md",
    "docs/onboarding/DEVELOPER_VISUAL_START_HERE.md",
    "docs/onboarding/repo_brain_context_intelligence.md",
    "docs/surrealdb/README.md",
    "tools/README.md",
    "tests/README.md",
    "services/README.md",
]

SECRET_PATH_DEFAULTS: list[str] = [
    str(Path.home() / "Documents" / ".secrets" / ".cdb"),
]

FORBIDDEN_OUTPUT_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?i)\b(token|secret|password|passwd|api[_-]?key)\s*[:=]\s*\S+"),
    re.compile(r"(?i)SURREAL_(?:PASS|USER)\s*=\s*\S+"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"https?://[^\s\"']+"),
    re.compile(r"(?i)(?:api|private|secret)_key[=:]\s*\S+"),
]


def _run_cmd(
    cmd: str,
    timeout: float = 15.0,
    runner: Callable[..., subprocess.CompletedProcess] | None = None,
) -> tuple[int, str, str]:
    kwargs: dict[str, Any] = {
        "capture_output": True,
        "text": True,
        "timeout": timeout,
        "errors": "replace",
    }
    if os.name == "nt":
        kwargs["shell"] = True
    else:
        kwargs["shell"] = False
    try:
        if runner is not None:
            proc = runner(cmd, **kwargs)
        else:
            proc = subprocess.run(cmd, **kwargs)  # noqa: S603
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        return proc.returncode, out, err
    except (
        FileNotFoundError,
        OSError,
        subprocess.TimeoutExpired,
        UnicodeDecodeError,
    ) as exc:
        return -1, "", str(exc)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


@dataclass
class CheckItem:
    name: str
    status: CheckResult
    detail: str = ""
    action: str = ""


@dataclass
class DoctorOutput:
    repo_root_found: CheckResult = "FAIL"
    git_found: CheckResult = "FAIL"
    git_branch: str = ""
    git_dirty: CheckResult = "SKIP"
    repo_head: str = ""
    python_found: CheckResult = "FAIL"
    python_version: str = ""
    python_version_ok: CheckResult = "FAIL"
    gh_found: CheckResult = "SKIP"
    gh_auth: CheckResult = "SKIP"
    docker_found: CheckResult = "SKIP"
    compose_found: CheckResult = "SKIP"
    env_file: CheckResult = "FAIL"
    secrets_path: CheckResult = "FAIL"
    secrets_resolved_dir: str = ""
    onboarding_files: CheckResult = "FAIL"
    context_doctor_reachable: CheckResult = "SKIP"
    lr_note: str = "NO-GO"
    warnings: list[str] = field(default_factory=list)
    checks: list[CheckItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo_root": self.repo_root_found,
            "repo_head": self.repo_head,
            "git": {
                "found": self.git_found,
                "branch": self.git_branch,
                "dirty": self.git_dirty,
                "head": self.repo_head,
            },
            "python": {
                "found": self.python_found,
                "version": self.python_version,
                "version_ok": self.python_version_ok,
            },
            "gh": {
                "found": self.gh_found,
                "auth": self.gh_auth,
            },
            "docker": {
                "found": self.docker_found,
                "compose": self.compose_found,
            },
            "env_file": self.env_file,
            "secrets_path": self.secrets_path,
            "secrets_resolved_dir": self.secrets_resolved_dir,
            "onboarding_files": self.onboarding_files,
            "context_doctor_reachable": self.context_doctor_reachable,
            "lr_note": self.lr_note,
            "warnings": self.warnings,
            "checks": [
                {
                    "name": c.name,
                    "status": c.status,
                    "detail": c.detail,
                    "action": c.action,
                }
                for c in self.checks
            ],
        }


def _parse_python_version(version_str: str) -> tuple[int, int, int] | None:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", version_str.strip())
    if match:
        return int(match.group(1)), int(match.group(2)), int(match.group(3))
    return None


def _version_ok(ver: tuple[int, int, int] | None) -> bool:
    if ver is None:
        return False
    major, minor, _ = ver
    return (major == 3 and minor >= 11) or major >= 4


def _check_secrets_path() -> tuple[CheckResult, str]:
    env_path = os.environ.get("SECRETS_PATH", "").strip()
    if env_path:
        p = Path(env_path)
        if p.is_dir():
            return "PASS", str(p)
        return "FAIL", f"SECRETS_PATH set but directory not found: {env_path}"
    for default in SECRET_PATH_DEFAULTS:
        p = Path(default)
        if p.is_dir():
            return "PASS", str(p)
    return "WARN", "SECRETS_PATH unset and no canonical secrets directory found"


def _check_env_file() -> tuple[CheckResult, str]:
    env_path = Path.cwd() / ".env"
    if env_path.is_file():
        return "PASS", ".env found"
    example = Path.cwd() / ".env.example"
    if example.is_file():
        return (
            "WARN",
            ".env missing, but .env.example exists (run: cp .env.example .env)",
        )
    return "FAIL", ".env missing and no .env.example found"


def _onboarding_files_exist(root: Path) -> tuple[CheckResult, list[str]]:
    missing: list[str] = []
    for rel_path in ONBOARDING_FILE_CHECKS:
        if not (root / rel_path).is_file():
            missing.append(rel_path)
    if not missing:
        return "PASS", []
    if len(missing) <= 2:
        return "WARN", missing
    return "FAIL", missing


def _check_context_doctor_reachable(
    runner: Callable[..., subprocess.CompletedProcess] | None = None,
) -> CheckResult:
    cmd = "python -m tools.surrealdb.context_onboarding_doctor --skip-mcp --skip-schema"
    rc, _, _ = _run_cmd(cmd, timeout=10.0, runner=runner)
    return "PASS" if rc == 0 else "WARN"


def _validate_output_safe(text: str) -> None:
    for pattern in FORBIDDEN_OUTPUT_PATTERNS:
        if pattern.search(text):
            raise ValueError(
                "output contains forbidden pattern — potential secret leak"
            )


def check_python_version(
    version_str: str, parser: Callable[[str], tuple[int, int, int] | None] | None = None
) -> tuple[CheckResult, str, CheckResult]:
    parse_fn = parser or _parse_python_version
    ver = parse_fn(version_str)
    if ver is None:
        return "WARN", version_str, "FAIL"
    ok = _version_ok(ver)
    if ok:
        return "PASS", f"{ver[0]}.{ver[1]}.{ver[2]}", "PASS"
    return "WARN", f"{ver[0]}.{ver[1]}.{ver[2]}", "FAIL"


def build_report(
    root: Path | None = None,
    *,
    git_runner: Callable[..., subprocess.CompletedProcess] | None = None,
    python_runner: Callable[..., subprocess.CompletedProcess] | None = None,
    gh_runner: Callable[..., subprocess.CompletedProcess] | None = None,
    docker_runner: Callable[..., subprocess.CompletedProcess] | None = None,
    compose_runner: Callable[..., subprocess.CompletedProcess] | None = None,
    context_doctor_runner: Callable[..., subprocess.CompletedProcess] | None = None,
) -> DoctorOutput:
    r = _repo_root() if root is None else root
    report = DoctorOutput()

    # Repo root
    if r.is_dir() and (r / ".git").is_dir() or (r / "README.md").is_file():
        report.repo_root_found = "PASS"
    else:
        report.repo_root_found = "FAIL"
        report.warnings.append("Repo root not detected — run from CDB repo root")

    # Git
    git_cmd = "git --version"
    rc, gout, gerr = _run_cmd(git_cmd, runner=git_runner)
    git_output = gout or gerr or ""
    report.git_found = "PASS" if (rc == 0 and git_output) else "FAIL"
    if report.git_found == "PASS":
        branch_cmd = "git rev-parse --abbrev-ref HEAD"
        _, branch_out, _ = _run_cmd(branch_cmd, runner=git_runner)
        report.git_branch = branch_out.strip() or "unknown"

        head_cmd = "git rev-parse HEAD"
        _, head_out, _ = _run_cmd(head_cmd, runner=git_runner)
        report.repo_head = head_out.strip() or ""

        status_cmd = "git status --porcelain"
        _, status_out, _ = _run_cmd(status_cmd, runner=git_runner)
        report.git_dirty = "WARN" if status_out.strip() else "PASS"
    else:
        report.git_branch = ""
        report.git_dirty = "SKIP"
        report.repo_head = ""

    # Python
    python_cmd = "python --version"
    rc, pout, perr = _run_cmd(python_cmd, runner=python_runner)
    py_output = pout or perr or ""
    if rc == 0 or (rc != -1 and py_output):
        report.python_found = "PASS" if py_output else "FAIL"
        if py_output:
            ver_status, ver_str, ver_ok = check_python_version(py_output)
            report.python_version = ver_str
            report.python_version_ok = ver_ok
    else:
        report.python_found = "FAIL"
        report.python_version = ""
        report.python_version_ok = "FAIL"

    # gh
    gh_cmd = "gh --version"
    rc, gh_out, gh_err = _run_cmd(gh_cmd, runner=gh_runner)
    gh_output = gh_out or gh_err or ""
    report.gh_found = "PASS" if (rc == 0 and gh_output) else "WARN"
    if report.gh_found == "PASS":
        auth_cmd = "gh auth status -h github.com"
        rc_auth, _, _ = _run_cmd(auth_cmd, runner=gh_runner)
        report.gh_auth = "PASS" if rc_auth == 0 else "WARN"
    else:
        report.gh_auth = "SKIP"

    # Docker
    docker_cmd = "docker --version"
    rc, dout, derr = _run_cmd(docker_cmd, runner=docker_runner)
    docker_output = dout or derr or ""
    report.docker_found = "PASS" if (rc == 0 and docker_output) else "WARN"
    if report.docker_found == "PASS":
        compose_cmd = "docker compose version"
        rc_c, cout, cerr = _run_cmd(compose_cmd, runner=compose_runner)
        compose_output = cout or cerr or ""
        report.compose_found = "PASS" if (rc_c == 0 and compose_output) else "WARN"
    else:
        report.compose_found = "SKIP"

    # .env
    env_status, env_detail = _check_env_file()
    report.env_file = env_status
    if env_status == "WARN":
        report.warnings.append(env_detail)

    # SECRETS_PATH
    secrets_status, secrets_detail = _check_secrets_path()
    report.secrets_path = secrets_status
    report.secrets_resolved_dir = secrets_detail

    # Onboarding files
    files_status, missing_files = _onboarding_files_exist(r)
    report.onboarding_files = files_status
    if missing_files:
        report.warnings.append(f"Missing onboarding files: {', '.join(missing_files)}")

    # Context doctor reachability
    doctor_status = _check_context_doctor_reachable(runner=context_doctor_runner)
    report.context_doctor_reachable = doctor_status
    if doctor_status != "PASS":
        report.warnings.append(
            "make context-doctor not reachable (run: make context-query-config-init)"
        )

    # Build per-check list
    report.checks = [
        CheckItem(name="Repo root", status=report.repo_root_found),
        CheckItem(name="Git", status=report.git_found, detail=report.git_branch),
        CheckItem(name="Git branch", status=report.git_dirty, detail=report.git_branch),
        CheckItem(
            name="Python", status=report.python_found, detail=report.python_version
        ),
        CheckItem(
            name="Python version",
            status=report.python_version_ok,
            detail=report.python_version,
        ),
        CheckItem(name="gh CLI", status=report.gh_found),
        CheckItem(name="gh auth", status=report.gh_auth),
        CheckItem(name="Docker", status=report.docker_found),
        CheckItem(name="Docker Compose", status=report.compose_found),
        CheckItem(name=".env file", status=report.env_file),
        CheckItem(
            name="SECRETS_PATH",
            status=report.secrets_path,
            detail=report.secrets_resolved_dir,
        ),
        CheckItem(name="Onboarding files", status=report.onboarding_files),
        CheckItem(name="make context-doctor", status=report.context_doctor_reachable),
    ]

    return report


def compute_exit_code(report: DoctorOutput) -> int:
    fails = [c for c in report.checks if c.status == "FAIL"]
    return 1 if fails else 0


def format_report(report: DoctorOutput, fmt: str) -> str:
    if fmt == "json":
        return json.dumps(report.to_dict(), indent=2, sort_keys=True)

    lines: list[str] = [
        "=== CDB Onboarding Doctor ===",
        f"lr_note: {report.lr_note}",
        "",
    ]

    status_icons = {"PASS": "OK", "WARN": "**", "FAIL": "!!", "SKIP": "--"}

    for check in report.checks:
        icon = status_icons.get(check.status, "??")
        line = f"  [{icon}] {check.name}"
        if check.detail:
            safe_detail = _safe_summary(check.detail, 80)
            line += f": {safe_detail}"
        lines.append(line)

    lines.append("")
    lines.append(
        f"  >> Secrets path: {_safe_summary(report.secrets_resolved_dir, 100)}"
    )
    lines.append(f"  >> .env: {report.env_file}")

    if report.warnings:
        lines.append("")
        lines.append("warnings:")
        for w in report.warnings:
            lines.append(f"  - {_safe_summary(w, 120)}")

    if report.context_doctor_reachable == "PASS":
        lines.append("")
        lines.append("  >> Onboarding looks usable. Run 'make context-doctor' for")
        lines.append("     Context Intelligence preflight.")
    else:
        lines.append("")
        lines.append(
            "  >> Run 'make context-query-config-init' then 'make context-doctor'"
        )
        lines.append("     for Context Intelligence preflight.")

    return "\n".join(lines)


def format_markdown_report(
    report: DoctorOutput,
    generated_at: str | None = None,
) -> str:
    if generated_at is None:
        generated_at = cdb_utcnow().isoformat(timespec="seconds")

    fail_count = sum(1 for c in report.checks if c.status == "FAIL")
    warn_count = sum(1 for c in report.checks if c.status == "WARN")
    pass_count = sum(1 for c in report.checks if c.status == "PASS")

    if fail_count > 0:
        overall = "FAIL"
    elif warn_count > 0:
        overall = "WARN"
    else:
        overall = "PASS"

    lines: list[str] = [
        "# CDB Onboarding Doctor Report",
        "",
        f"**Generated**: {generated_at}",
        f"**Repo HEAD**: {report.repo_head or 'unknown'}",
        f"**Branch**: {report.git_branch or 'unknown'}",
        "",
        "## Summary",
        "",
        f"- **PASS**: {pass_count}",
        f"- **WARN**: {warn_count}",
        f"- **FAIL**: {fail_count}",
        f"- **Overall**: {overall}",
        "",
        "## Safety Boundaries",
        "",
        "- LR remains **NO-GO**.",
        "- Board stage `trade-capable` is **not** a Live-Go.",
        "- No Echtgeld-Go.",
        "- This report is read-only evidence; no runtime, Docker, DB, or MCP actions performed.",
        "- No secret values are included in this report.",
        "",
        "## Repo State",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| HEAD | `{report.repo_head or 'unknown'}` |",
        f"| Branch | `{report.git_branch or 'unknown'}` |",
        f"| Working tree | {report.git_dirty} |",
        f"| Secrets path | {_safe_summary(report.secrets_resolved_dir, 120)} |",
        f"| .env | {report.env_file} |",
        "",
        "## Checks",
        "",
        "| Check | Status | Detail |",
        "|-------|--------|--------|",
    ]

    for check in report.checks:
        detail = check.detail.replace("|", "\\|") if check.detail else ""
        lines.append(f"| {check.name} | {check.status} | {detail} |")

    lines.extend(
        [
            "",
            "## Active Onboarding Surfaces",
            "",
        ]
    )
    for rel_path in ONBOARDING_FILE_CHECKS:
        lines.append(f"- `{rel_path}`")

    if report.warnings:
        lines.extend(
            [
                "",
                "## Warnings",
                "",
            ]
        )
        for w in report.warnings:
            lines.append(f"- {_safe_summary(w, 200)}")

    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- Local checks only; no runtime, Docker, DB, or MCP mutation.",
            "- Context Doctor reachability is a check only, not a full preflight.",
            "- No container, network, or stack validation.",
            "- No external-API or exchange-connectivity validation.",
            "",
            "---",
            "",
            f"*Report generated by `tools/onboarding_doctor.py` ({overall})*",
        ]
    )

    return "\n".join(lines) + "\n"


def _safe_summary(text: str, max_len: int = 80) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


_HELP_EPILOG = """\
Examples:
  python -m tools.onboarding_doctor
  python -m tools.onboarding_doctor --format json
  python -m tools.onboarding_doctor --report docs/evidence/local_onboarding_check.md
  .\\tools\\cdb.ps1 onboarding doctor
  .\\tools\\cdb.ps1 onboarding doctor --report docs/evidence/local_onboarding_check.md
  make onboarding-doctor

Exit codes:
  0  all checks PASS or only non-blocking WARN
  1  one or more FAIL checks
  2  CLI usage error
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only onboarding doctor for CDB developer setup.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_HELP_EPILOG,
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--report",
        metavar="PATH",
        help="Write a Markdown report to PATH (opt-in; default: no file written)",
    )
    args = parser.parse_args(argv)

    if args.format not in ("text", "json"):
        print("ERROR: unsupported --format", file=sys.stderr)
        return 2

    report = build_report()
    output = format_report(report, args.format)
    _validate_output_safe(output)
    print(output)

    if args.report:
        try:
            generated_at = cdb_utcnow().isoformat(timespec="seconds")
            md = format_markdown_report(report, generated_at)
            _validate_output_safe(md)
            report_path = Path(args.report)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(md, encoding="utf-8")
            print(
                f"Markdown report written to: {report_path.resolve()}",
                file=sys.stderr,
            )
        except (OSError, ValueError) as exc:
            print(f"ERROR: cannot write report: {exc}", file=sys.stderr)
            return 2

    return compute_exit_code(report)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
