"""Execute Pack-A wave-1 offline shape/replay for issue #3780.

Safety boundaries:
- offline file-backed replay only
- no Docker / no paper runtime
- ranking_ready=false
- no natural_paper_evidence claim
"""

# ruff: noqa: E402

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.replay.pack_a_breakout_common import (
    BREAKOUT_TREND_FILTER_STRATEGY_ID,
    DONCHIAN_BREAKOUT_STRATEGY_ID,
)
from services.validation.strategy_replay_runner import ARVPReplayConfig, run_arvp_replay

ISSUE = "#3780"
PARENT_ISSUE = "#1900"
SPEC_ISSUE = "#3748"
LR_STATUS = "NO-GO"
RANKING_READY = False

PINNED_DATASET = (
    REPO_ROOT
    / "artifacts"
    / "backtests"
    / "primary_breakout_v1"
    / "20260418-212643"
    / "dataset.candles.json"
)
OUTPUT_ROOT = REPO_ROOT / "artifacts" / "replay_reports" / "pack_a_wave1_3780"
MANIFEST_PATH = OUTPUT_ROOT / "pack_a_wave1_manifest.json"
EVIDENCE_DOC = (
    REPO_ROOT / "docs" / "evidence" / "arvp_pack_a_wave1_shape_replay_3780.md"
)

SCENARIO_IDS = ("baseline", "pessimistic_execution", "feed_gap")

PACK_A_CANDIDATES: tuple[tuple[str, str, str], ...] = (
    ("primary_breakout_v1", "primary_breakout_runner_v1", "PARKED reference anchor"),
    (DONCHIAN_BREAKOUT_STRATEGY_ID, "donchian_breakout_runner_v1", "external breakout benchmark"),
    (
        BREAKOUT_TREND_FILTER_STRATEGY_ID,
        "breakout_trend_filter_runner_v1",
        "breakout + trend gate comparison",
    ),
)


@dataclass(frozen=True, slots=True)
class CandidateResult:
    strategy_id: str
    role: str
    exit_code: int
    artifact_root: str
    dataset_fingerprint: str | None
    scenario_manifest_path: str | None
    deterministic_rerun_ok: bool
    verdict: str
    sub_status: str
    metrics_summary: dict[str, Any]


def _git_head() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=REPO_ROOT,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _summarize_metrics(manifest_path: Path) -> dict[str, Any]:
    manifest = _load_json(manifest_path)
    summary: dict[str, Any] = {
        "group_id": manifest.get("group_id"),
        "group_fingerprint": manifest.get("group_fingerprint"),
        "failed_count": manifest.get("failed_count"),
        "succeeded_count": manifest.get("succeeded_count"),
        "scenarios": {},
    }
    manifest_dir = manifest_path.parent
    for result in manifest.get("scenario_results", []):
        scenario_id = result.get("scenario_id")
        if not scenario_id:
            continue
        metrics_path = manifest_dir / f"{scenario_id}_metrics.json"
        if metrics_path.is_file():
            payload = _load_json(metrics_path)
            summary["scenarios"][scenario_id] = {
                "run_id": payload.get("run_id"),
                "signals_total": payload.get("metrics", {}).get("signals_total"),
                "closed_trades_total": payload.get("metrics", {}).get(
                    "closed_trades_total"
                ),
                "fee_adjusted_return_r": payload.get("metrics", {}).get(
                    "fee_adjusted_return_r"
                ),
                "max_drawdown_r": payload.get("metrics", {}).get("max_drawdown_r"),
                "ranking_ready": payload.get("metrics", {}).get("ranking_ready", False),
            }
        else:
            summary["scenarios"][scenario_id] = {
                "run_id": result.get("run_id"),
                "exit_code": result.get("exit_code"),
            }
    return summary


def _run_candidate(strategy_id: str, adapter_id: str, role: str) -> CandidateResult:
    out_dir = OUTPUT_ROOT / strategy_id
    out_dir.mkdir(parents=True, exist_ok=True)
    config = ARVPReplayConfig(
        dataset_source="file",
        input_candles_file=str(PINNED_DATASET),
        strategy_id=strategy_id,
        symbol="BTCUSDT",
        adapter_id=adapter_id,
        output_directory=str(out_dir),
        scenario_ids=SCENARIO_IDS,
        scenario_group_id=f"pack_a_wave1_{strategy_id}",
    )
    config.validate()
    exit_code = run_arvp_replay(config)

    manifests = sorted(out_dir.glob("**/scenario_group_manifest.json"))
    manifest_path = manifests[-1] if manifests else None
    dataset_fingerprint = None
    metrics_summary: dict[str, Any] = {}
    deterministic_rerun_ok = False
    if manifest_path is not None:
        manifest = _load_json(manifest_path)
        dataset_fingerprint = manifest.get("group_fingerprint")
        metrics_summary = _summarize_metrics(manifest_path)
        deterministic_rerun_ok = manifest.get("failed_count", 1) == 0 and exit_code == 0

    if exit_code != 0 or not deterministic_rerun_ok:
        verdict = "FAIL"
    else:
        verdict = "PASS"

    return CandidateResult(
        strategy_id=strategy_id,
        role=role,
        exit_code=exit_code,
        artifact_root=str(out_dir),
        dataset_fingerprint=dataset_fingerprint,
        scenario_manifest_path=str(manifest_path) if manifest_path else None,
        deterministic_rerun_ok=deterministic_rerun_ok,
        verdict=verdict,
        sub_status="NOT_RANKING_READY",
        metrics_summary=metrics_summary,
    )


def _render_evidence_doc(
    *,
    head_sha: str,
    dataset_sha256: str,
    results: list[CandidateResult],
) -> str:
    lines = [
        "# ARVP Pack-A Wave-1 Shape/Replay Evidence (#3780)",
        "",
        f"Status Class: offline shape/replay execute (no promotion, no paper claim)",
        f"Issue: {ISSUE}",
        f"Parent: {PARENT_ISSUE}",
        f"Spec: {SPEC_ISSUE}",
        f"Live-Readiness: **{LR_STATUS}**",
        f"Echtgeld: **not authorized**",
        f"ranking_ready: **false**",
        f"natural_paper_evidence: **false**",
        "",
        "## Brain Evidence",
        "",
        "```text",
        "brain_source: repo-only",
        "brain_status: not-used",
        "tools_or_queries:",
        "  - git fetch/status/rev-parse; gh issue view 3780,3748,3747,3742,1900",
        "  - MCP cdb_context_briefing attempted — unknown_tool on context_briefing alias",
        "  - run_pack_a_wave1_shape_replay_3780.py offline replay execution",
        "records_or_results:",
        "  - context_brain_attempted=true; context_brain_used=false; context_available=false",
        "  - repo_fallback_reason=tool_blocked; records_found=none",
        f"  - HEAD={head_sha}",
        f"  - dataset_sha256={dataset_sha256}",
        "repo_crosscheck:",
        "  - docs/evidence/arvp_pack_a_breakout_baseline_spec_3748.md",
        "  - services/validation/strategy_replay_runner.py",
        "  - core/replay/scenario_packs.py",
        "impact_on_plan:",
        "  - Implemented minimal Donchian + Breakout+Trend adapters; executed Top-3 offline.",
        "limitations:",
        "  - No SurrealDB records; B1 friction gap unchanged; #3035 formal report not re-emitted.",
        "  - deterministic_replay_ok two-pass only for primary_breakout_v1.",
        "context_brain_attempted: true",
        "context_brain_used: false",
        "context_available: false",
        "repo_fallback_used: true",
        "repo_fallback_reason: tool_blocked",
        "context_tool_status: partial",
        "context_trust_level: none",
        "records_found: none",
        "```",
        "",
        "## Scope and Human-GO boundary",
        "",
        "- Offline replay only; no Docker paper runtime; no fresh-paper observation.",
        "- ranking_ready=false; no natural_paper_evidence; LR NO-GO unchanged.",
        "- PB1 PARKED reference only — no rescue/promotion.",
        "",
        "## Dataset and quality gate",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| path | `{PINNED_DATASET.relative_to(REPO_ROOT).as_posix()}` |",
        f"| sha256 | `{dataset_sha256}` |",
        f"| symbol | BTCUSDT |",
        f"| timeframe | 1m |",
        f"| #3035 report | not re-emitted — technical replay validity only (WARNING banner) |",
        "",
        "## Execution matrix",
        "",
        "| strategy_id | role | scenarios | exit | verdict | sub_status |",
        "|-------------|------|-----------|------|---------|------------|",
    ]
    for result in results:
        lines.append(
            f"| `{result.strategy_id}` | {result.role} | {','.join(SCENARIO_IDS)} | "
            f"{result.exit_code} | **{result.verdict}** | {result.sub_status} |"
        )

    lines.extend(
        [
            "",
            "## Scenario results (summary)",
            "",
        ]
    )
    for result in results:
        lines.append(f"### `{result.strategy_id}`")
        lines.append("")
        lines.append(f"- artifact_root: `{result.artifact_root}`")
        if result.scenario_manifest_path:
            lines.append(f"- manifest: `{result.scenario_manifest_path}`")
        lines.append(f"- dataset_fingerprint: `{result.dataset_fingerprint}`")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(result.metrics_summary, indent=2, sort_keys=True))
        lines.append("```")
        lines.append("")

    lines.extend(
        [
            "## Deterministic rerun parity",
            "",
            "- Scenario group manifests with `failed_count=0` treated as deterministic rerun OK for this slice.",
            "- Pack-A Donchian/Bo+Trend runners use single-pass reports (`deterministic_replay_ok=false` by design).",
            "- PB1 retains native two-pass determinism check when run standalone.",
            "",
            "## Limitations",
            "",
            "- B1 same-venue friction evidence missing (#3747) — economics advisory only.",
            "- ranking_ready=false for all candidates.",
            "- No §5.2.4 / Product-Complete / natural_paper_evidence claim.",
            "- LR remains NO-GO.",
            "",
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    if not PINNED_DATASET.is_file():
        print(f"ERROR: pinned dataset missing: {PINNED_DATASET}", file=sys.stderr)
        return 2

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    head_sha = _git_head()
    dataset_sha256 = _sha256_file(PINNED_DATASET)

    results = [
        _run_candidate(strategy_id, adapter_id, role)
        for strategy_id, adapter_id, role in PACK_A_CANDIDATES
    ]

    manifest = {
        "issue": ISSUE,
        "parent_issue": PARENT_ISSUE,
        "spec_issue": SPEC_ISSUE,
        "head_sha": head_sha,
        "dataset_path": str(PINNED_DATASET),
        "dataset_sha256": dataset_sha256,
        "ranking_ready": RANKING_READY,
        "natural_paper_evidence": False,
        "lr_status": LR_STATUS,
        "scenario_ids": list(SCENARIO_IDS),
        "candidates": [
            {
                "strategy_id": r.strategy_id,
                "role": r.role,
                "exit_code": r.exit_code,
                "verdict": r.verdict,
                "sub_status": r.sub_status,
                "artifact_root": r.artifact_root,
                "scenario_manifest_path": r.scenario_manifest_path,
                "dataset_fingerprint": r.dataset_fingerprint,
                "metrics_summary": r.metrics_summary,
            }
            for r in results
        ],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    EVIDENCE_DOC.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DOC.write_text(
        _render_evidence_doc(
            head_sha=head_sha,
            dataset_sha256=dataset_sha256,
            results=results,
        ),
        encoding="utf-8",
    )

    failed = [r for r in results if r.exit_code != 0]
    print(f"Pack-A wave-1 complete: manifest={MANIFEST_PATH}")
    print(f"Evidence doc: {EVIDENCE_DOC}")
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
