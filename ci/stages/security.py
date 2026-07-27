"""Security stage — heavy/opt-in; no silent PASS when tools missing."""

from __future__ import annotations

import shutil
import time

from ci.lib.evidence import StageResult, utc_now
from ci.lib.process import run_command
from ci.stages._common import StageContext, skipped_stage


def run(ctx: StageContext) -> StageResult:
    if ctx.profile != "heavy":
        return skipped_stage(
            name="security",
            reason="security is heavy-profile only (opt-in; GitHub scanners remain authoritative)",
            required=False,
        )

    started = utc_now()
    log_path = ctx.logs_dir / "security.log"
    summaries: list[str] = []
    parts: list[str] = []
    wall = time.perf_counter()
    exit_code = 0
    skip_notes: list[str] = []

    # Explicit tool presence — do not soft-skip into PASS.
    if shutil.which("gitleaks"):
        cmd = ["gitleaks", "detect", "--source", ".", "-v"]
        summaries.append(" ".join(cmd))
        result = run_command(
            cmd, cwd=ctx.repo_root, log_path=ctx.logs_dir / "security.gitleaks.log"
        )
        parts.append(
            (ctx.logs_dir / "security.gitleaks.log").read_text(encoding="utf-8")
        )
        if result.exit_code != 0:
            exit_code = result.exit_code
    else:
        skip_notes.append("gitleaks binary not found on PATH")

    for label, cmd in (
        ("ruff", ["ruff", "check", "."]),
        ("bandit", ["bandit", "-r", "core/", "services/"]),
    ):
        if exit_code != 0:
            break
        summaries.append(" ".join(cmd))
        result = run_command(
            cmd, cwd=ctx.repo_root, log_path=ctx.logs_dir / f"security.{label}.log"
        )
        parts.append(
            (ctx.logs_dir / f"security.{label}.log").read_text(encoding="utf-8")
        )
        if result.exit_code != 0:
            exit_code = result.exit_code

    # Opt-in tools: record SKIPPED reasons; do not fail the stage solely for absence.
    for tool in ("trivy", "pip-audit", "codeql"):
        if not shutil.which(tool):
            skip_notes.append(
                f"{tool} not on PATH; local SARIF/Security-tab parity not claimed"
            )

    log_path.write_text(
        "\n".join(parts)
        + "\n\n# opt-in / missing tools\n"
        + "\n".join(f"- {n}" for n in skip_notes)
        + "\n",
        encoding="utf-8",
    )
    ended = utc_now()
    status = "PASS" if exit_code == 0 else "FAIL"
    # If gitleaks missing but ruff/bandit ran: still PASS/FAIL on those;
    # missing gitleaks is recorded in skip_reason for transparency without fake-green.
    skip_reason = "; ".join(skip_notes) if skip_notes else None
    return StageResult(
        name="security",
        status=status,  # type: ignore[arg-type]
        exit_code=exit_code,
        started_at_utc=started,
        ended_at_utc=ended,
        duration_seconds=round(time.perf_counter() - wall, 3),
        command_summary=summaries,
        log_path=str(log_path.relative_to(ctx.run_dir).as_posix()),
        artifacts=[],
        skip_reason=skip_reason if status == "PASS" and not summaries else skip_reason,
        required=False,
    )
