"""Shared helpers for Test Pack contract tests (#3873–#3879)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
TEST_PACK_ROOT = REPO_ROOT / "tools" / "test_pack"
FIXTURES_ROOT = REPO_ROOT / "tests" / "fixtures" / "test_pack"

PACK_MANIFEST_JSON = TEST_PACK_ROOT / "PACK_MANIFEST.json"
PACK_MANIFEST_YAML = TEST_PACK_ROOT / "pack" / "manifest.yaml"
SCENARIO_CATALOG = TEST_PACK_ROOT / "scenarios" / "catalog.yaml"
EVIDENCE_README_TEMPLATE = TEST_PACK_ROOT / "templates" / "evidence_pack_README.md"
OPERATOR_DRILL_SCRIPT = TEST_PACK_ROOT / "tools" / "drills" / "trigger-operator-drill.ps1"
KILL_SWITCH_CHECKLIST_REPO = REPO_ROOT / "docs" / "operations" / "KILL_SWITCH_OPERATOR_CHECKLIST.md"
MOCK_EXCHANGE_SHIM = TEST_PACK_ROOT / "tools" / "mock_exchange" / "mock_exchange.py"
CHAOS_GENERATE_SCENARIO = TEST_PACK_ROOT / "tools" / "chaos" / "generate_scenario.py"
EVALUATE_ASSERTIONS_SCRIPT = TEST_PACK_ROOT / "tools" / "assertions" / "evaluate_assertions.py"
METRICS_SNAPSHOT_SCRIPT = TEST_PACK_ROOT / "tools" / "metrics" / "metrics_snapshot.py"
METRICS_SMOKE_PS1 = TEST_PACK_ROOT / "tools" / "metrics" / "metrics-smoke.ps1"
METRICS_MATRIX_DOC = REPO_ROOT / "infrastructure" / "monitoring" / "METRICS_MATRIX.md"
LR041_RUNNER = REPO_ROOT / "scripts" / "drills" / "lr041_redis_postgres_failure_runner.py"
LR042_RUNNER = REPO_ROOT / "scripts" / "drills" / "lr042_network_latency_packet_loss_runner.py"
MOCKEXCHANGE_TEST_MAP = REPO_ROOT / "knowledge" / "testing" / "MOCKEXCHANGE_CDB_TEST_MAP.md"
TEST_PACK_README = TEST_PACK_ROOT / "README.md"
ISSUE_PACK_ROOT = TEST_PACK_ROOT / "issue_pack"
ISSUE_PACK_README = ISSUE_PACK_ROOT / "README.md"
PROMPT_IMPORT_TESTPACK = TEST_PACK_ROOT / "prompts" / "PROMPT_CodeX_Import_TestPack_v2.md"
PROMPT_ISSUE_PACK = TEST_PACK_ROOT / "prompts" / "PROMPT_CodeX_IssuePack_CDB_LiveReadiness.md"
CHAOS_DRILL_SCRIPT = TEST_PACK_ROOT / "infrastructure" / "scripts" / "run-chaos-drill.ps1"
PLANNING_LINT_SCRIPT = TEST_PACK_ROOT / "tools" / "planning" / "planning_lint.py"

README_FROZEN_STATUS_MARKERS: tuple[str, ...] = (
    "Frozen experimental",
    "import snapshot",
    "Not maintained as an active repo path",
)

README_QUICKSTART_TOOL_PATHS: tuple[str, ...] = (
    "tools/chaos/generate_scenario.py",
    "infrastructure/scripts/run-chaos-drill.ps1",
    "tools/drills/trigger-operator-drill.ps1",
    "tools/mock_exchange/mock_exchange.py",
)

README_EXTENSION_TOOL_PATHS: tuple[str, ...] = (
    "tools/assertions/evaluate_assertions.py",
    "tools/metrics/metrics_snapshot.py",
    "scenarios/catalog.yaml",
)

ISSUE_PACK_PROMPT_REFS: tuple[str, ...] = (
    "prompts/PROMPT_CodeX_IssuePack_CDB_LiveReadiness.md",
)

STALE_TODO_HOOK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"TODO hooks for ingestion \+ metrics/assertions", re.I),
    re.compile(r"Known gaps / TODOs?", re.I),
    re.compile(r"adapters/ADAPTERS\.md", re.I),
)

STALE_OPTIONAL_PACK_PATHS = frozenset(
    {
        "adapters/ADAPTERS.md",
        "tools/test_pack/adapters/ADAPTERS.md",
    }
)

PACK_RELATIVE_PATH_PATTERN = re.compile(
    r"(?<![\w./])"
    r"(?:tools|scenarios|templates|runbooks|prompts|issue_pack|pack|infrastructure)/"
    r"[\w./-]+\.(?:py|ps1|yaml|yml|md|json|jsonl|txt)"
)

NO_AUTO_FIX_FORBIDDEN_SOURCE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bgh\s+issue\s+create\b"),
    re.compile(r"\bsubprocess\.run\b"),
    re.compile(r"\.write_text\("),
    re.compile(r"\.write_bytes\("),
)

CANONICAL_REDIS_CONTAINER = "cdb_redis"
VALKEY_DRIFT_PATTERNS = (
    re.compile(r"mockx-valkey"),
    re.compile(r"\bVALKEY_HOST\b"),
    re.compile(r"\bvalkey\b", re.I),
)

VERDICT_VALUES = frozenset({"PASS", "WARN", "FAIL"})
KILL_SWITCH_STATES = frozenset({"active", "inactive", "unknown"})

SECRET_PATTERNS = (
    re.compile(r"(?i)password\s*[:=]"),
    re.compile(r"(?i)api[_-]?key\s*[:=]"),
    re.compile(r"(?i)secret\s*[:=]"),
    re.compile(r"(?i)bearer\s+[a-z0-9._-]{8,}", re.I),
)

EVIDENCE_TEMPLATE_REQUIRED_ANCHORS: tuple[str, ...] = (
    "Date/Time (UTC)",
    "Operator (if drill)",
    "PASS/FAIL",
    "Required artifacts",
    "sources_manifest.txt",
    "run_config.json",
    "timeline",
)

OPERATOR_ACTION_EVENTS = frozenset(
    {
        "ALERT_TRIGGERED",
        "VERIFY_KILL_SWITCH_ACTIVE",
        "VERIFY_KILL_SWITCH_INACTIVE",
        "VERIFY_KILL_SWITCH_ERROR",
        "DRILL_START",
        "DRILL_END",
    }
)

TIMESTAMP_FIELD_NAMES = frozenset({"ts", "ts_utc", "timestamp", "verified_at"})

LIVE_DEFAULT_FORBIDDEN = (
  re.compile(r"(?i)\blive[_-]?trading\b"),
  re.compile(r"(?i)\bechtgeld\b"),
  re.compile(r"(?i)\breal[_-]?orders?\b"),
  re.compile(r"(?i)\bproduction[_-]?runtime\b"),
)


def load_pack_manifest_json() -> dict[str, Any]:
    return json.loads(PACK_MANIFEST_JSON.read_text(encoding="utf-8"))


def load_pack_manifest_yaml() -> dict[str, Any]:
    return yaml.safe_load(PACK_MANIFEST_YAML.read_text(encoding="utf-8"))


def load_scenario_catalog() -> dict[str, Any]:
    return yaml.safe_load(SCENARIO_CATALOG.read_text(encoding="utf-8"))


PACK_ROOT_PREFIXES = (
    "templates/",
    "runbooks/",
    "pack/",
    "scenarios/",
    "infrastructure/",
    "prompts/",
    "issue_pack/",
)

PACK_ROOT_FILES = frozenset({"README.md", "PACK_MANIFEST.json", "CHANGELOG.md"})


def resolve_pack_relative(relative_path: str) -> Path:
    normalized = relative_path.replace("\\", "/").lstrip("/")
    if normalized.startswith("tools/"):
        normalized = normalized.removeprefix("tools/")
    if normalized.startswith(PACK_ROOT_PREFIXES) or normalized in PACK_ROOT_FILES:
        return TEST_PACK_ROOT / normalized
    return TEST_PACK_ROOT / "tools" / normalized


def scenario_artifact_paths(scenario: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for key in ("generator", "trigger", "server", "evidence"):
        value = scenario.get(key)
        if isinstance(value, str) and value.strip():
            paths.append(value.strip())
    return paths


def collect_missing_scenario_artifacts(catalog: dict[str, Any]) -> dict[str, list[str]]:
    missing: dict[str, list[str]] = {}
    for scenario in catalog.get("scenarios", []):
        scenario_id = scenario.get("id", "<unknown>")
        gaps: list[str] = []
        for rel in scenario_artifact_paths(scenario):
            candidate = resolve_pack_relative(rel)
            if not candidate.exists():
                gaps.append(rel)
        if gaps:
            missing[scenario_id] = gaps
    return missing


def assert_no_live_defaults_in_text(text: str, *, label: str) -> list[str]:
    violations: list[str] = []
    for pattern in LIVE_DEFAULT_FORBIDDEN:
        if pattern.search(text):
            violations.append(f"{label}: forbidden live-default phrase {pattern.pattern!r}")
    return violations


def scan_text_for_secrets(text: str) -> list[str]:
    findings: list[str] = []
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            findings.append(f"secret-like pattern matched: {pattern.pattern!r}")
    return findings


@dataclass(frozen=True)
class EvidencePackScore:
    verdict: Literal["PASS", "WARN", "FAIL"]
    reasons: tuple[str, ...]
    missing_fields: tuple[str, ...]


def _timeline_has_timestamp(events: list[dict[str, Any]]) -> bool:
    for event in events:
        if any(field in event for field in TIMESTAMP_FIELD_NAMES):
            return True
    return False


def score_operator_evidence_pack(pack: dict[str, Any]) -> EvidencePackScore:
    """Fixture-based operator evidence pack scoring — simulation only."""
    missing: list[str] = []
    reasons: list[str] = []

    readme = pack.get("readme_text", "")
    if not readme.strip():
        missing.append("readme_text")
    else:
        for anchor in EVIDENCE_TEMPLATE_REQUIRED_ANCHORS:
            if anchor not in readme:
                missing.append(f"readme_anchor:{anchor}")

    timeline = pack.get("timeline", [])
    if not isinstance(timeline, list) or not timeline:
        missing.append("timeline")
    elif not _timeline_has_timestamp(timeline):
        missing.append("timeline_timestamp")

    operator_events = {
        e.get("event")
        for e in timeline
        if isinstance(e, dict) and isinstance(e.get("event"), str)
    }
    if not operator_events & OPERATOR_ACTION_EVENTS:
        missing.append("operator_action_event")

    run_config = pack.get("run_config", {})
    if not isinstance(run_config, dict) or not run_config.get("ts_utc"):
        missing.append("run_config.ts_utc")
    if not run_config.get("drill_type"):
        missing.append("run_config.drill_type")

    verdict_payload = pack.get("drill_verdict", {})
    declared_verdict = verdict_payload.get("verdict") if isinstance(verdict_payload, dict) else None
    if declared_verdict not in VERDICT_VALUES:
        missing.append("drill_verdict.verdict")

    verification = pack.get("kill_switch_verification", {})
    ks_active = None
    if isinstance(verification, dict):
        ks_active = verification.get("kill_switch_active")

    secret_hits = scan_text_for_secrets(json.dumps(pack, ensure_ascii=False))
    if secret_hits:
        reasons.extend(secret_hits)
        return EvidencePackScore("FAIL", tuple(reasons), tuple(missing))

    if missing:
        reasons.append("missing required operator evidence")
        return EvidencePackScore("FAIL", tuple(reasons), tuple(missing))

    if ks_active is None:
        reasons.append("unknown kill-switch state is not PASS")
        return EvidencePackScore("FAIL", tuple(reasons), ("kill_switch_verification.kill_switch_active",))

    if declared_verdict == "PASS" and ks_active is not True:
        reasons.append("declared PASS but kill-switch not active")
        return EvidencePackScore("FAIL", tuple(reasons), ())

    if declared_verdict == "WARN":
        return EvidencePackScore("WARN", tuple(reasons or ("partial evidence acceptable",)), ())

    return EvidencePackScore("PASS", tuple(reasons), ())


@dataclass(frozen=True)
class KillSwitchDrillSimulationResult:
    verdict: Literal["PASS", "WARN", "FAIL"]
    kill_switch_state: str
    timeline_events: tuple[str, ...]
    fail_reasons: tuple[str, ...]
    evidence_artifacts: tuple[str, ...]


def simulate_kill_switch_drill(
    *,
    kill_switch_state: Literal["active", "inactive", "unknown"],
    operator_activated: bool,
    alert_triggered: bool = True,
    lr003_passed: bool = True,
) -> KillSwitchDrillSimulationResult:
    """Local simulation of operator kill-switch drill — no runtime side effects."""
    if kill_switch_state not in KILL_SWITCH_STATES:
        kill_switch_state = "unknown"

    timeline: list[str] = ["DRILL_START"]
    if alert_triggered:
        timeline.append("ALERT_TRIGGERED")
    if operator_activated and kill_switch_state == "active":
        timeline.append("VERIFY_KILL_SWITCH_ACTIVE")
    elif kill_switch_state == "inactive":
        timeline.append("VERIFY_KILL_SWITCH_INACTIVE")
    elif kill_switch_state == "unknown":
        timeline.append("VERIFY_KILL_SWITCH_ERROR")
    else:
        timeline.append("VERIFY_KILL_SWITCH_INACTIVE")
    if lr003_passed:
        timeline.append("LR003_DRILL_PASS")
    timeline.append("DRILL_END")

    artifacts = (
        "timeline.json",
        "drill_verdict.json",
        "reports/kill_switch_verification.json",
        "run_config.json",
    )

    fail_reasons: list[str] = []
    if kill_switch_state == "unknown":
        fail_reasons.append("kill-switch state not verifiable")
    if not alert_triggered:
        fail_reasons.append("console alert was not triggered")
    if kill_switch_state != "active":
        fail_reasons.append("kill-switch was not active after operator wait")
    if not lr003_passed:
        fail_reasons.append("LR-003 fail-closed gate drill did not pass")

    if kill_switch_state == "unknown":
        verdict: Literal["PASS", "WARN", "FAIL"] = "FAIL"
    elif fail_reasons:
        verdict = "FAIL"
    else:
        verdict = "PASS"

    return KillSwitchDrillSimulationResult(
        verdict=verdict,
        kill_switch_state=kill_switch_state,
        timeline_events=tuple(timeline),
        fail_reasons=tuple(fail_reasons),
        evidence_artifacts=artifacts,
    )


@dataclass(frozen=True)
class MockExchangeOrderSimulation:
    http_status: int
    order_status: str | None
    error: str | None = None
    filled_qty: float | None = None


def simulate_mock_exchange_order(
    *,
    symbol: str,
    side: str,
    qty: float,
    price: float | None = None,
    partial_fill_ratio: float = 1.0,
) -> MockExchangeOrderSimulation:
    """Contract simulation of Test Pack mock_exchange shim — no HTTP, no live exchange."""
    try:
        normalized_side = str(side).upper()
        normalized_qty = float(qty)
        if normalized_side not in {"BUY", "SELL"} or normalized_qty <= 0:
            raise ValueError("bad_order")
        if not str(symbol).strip():
            raise ValueError("bad_symbol")
    except (TypeError, ValueError):
        return MockExchangeOrderSimulation(400, None, error="bad_order_payload")

    if price is None:
        return MockExchangeOrderSimulation(200, "NEW")

    if partial_fill_ratio < 1.0:
        if partial_fill_ratio <= 0:
            return MockExchangeOrderSimulation(200, "REJECTED", filled_qty=0.0)
        filled = round(normalized_qty * partial_fill_ratio, 8)
        return MockExchangeOrderSimulation(200, "PARTIAL", filled_qty=filled)

    return MockExchangeOrderSimulation(200, "FILLED", filled_qty=normalized_qty)


def simulate_mock_exchange_cancel(
    *,
    order_status: str,
) -> MockExchangeOrderSimulation:
    if order_status in {"FILLED", "CANCELED"}:
        return MockExchangeOrderSimulation(200, order_status)
    if order_status == "NEW":
        return MockExchangeOrderSimulation(200, "CANCELED")
    return MockExchangeOrderSimulation(404, None, error="unknown_order")


def scan_text_for_valkey_drift(text: str, *, label: str) -> list[str]:
    violations: list[str] = []
    for pattern in VALKEY_DRIFT_PATTERNS:
        if pattern.search(text):
            violations.append(f"{label}: valkey drift pattern {pattern.pattern!r}")
    return violations


def extract_prometheus_values(result_payload: dict[str, Any]) -> list[float]:
    data = result_payload.get("data", {}) if isinstance(result_payload, dict) else {}
    items = data.get("data", {}).get("result", []) if isinstance(data, dict) else []
    values: list[float] = []
    for item in items:
        value = item.get("value")
        if isinstance(value, list) and len(value) == 2:
            try:
                values.append(float(value[1]))
            except ValueError:
                continue
    return values


@dataclass(frozen=True)
class ChaosAssertionEvaluation:
    overall_pass: bool
    failed_ids: tuple[str, ...]
    assertion_count: int


def evaluate_chaos_assertions_from_snapshot(snapshot: dict[str, Any]) -> ChaosAssertionEvaluation:
    """Mirror evaluate_assertions.py semantics for fixture-based contract tests."""
    assertions: list[dict[str, Any]] = []
    queries = snapshot.get("queries", {}) if isinstance(snapshot, dict) else {}

    up_vals = extract_prometheus_values(queries.get("up_cdb", {}))
    up_pass = bool(up_vals) and all(v >= 1 for v in up_vals)
    assertions.append({"id": "up_cdb", "pass": up_pass})

    cb_vals = extract_prometheus_values(queries.get("circuit_breaker_active", {}))
    assertions.append({"id": "circuit_breaker_metric", "pass": bool(cb_vals)})

    approved = extract_prometheus_values(queries.get("orders_approved_total", {}))
    blocked = extract_prometheus_values(queries.get("orders_blocked_total", {}))
    assertions.append(
        {"id": "orders_metrics_present", "pass": bool(approved) or bool(blocked)}
    )

    failed = tuple(a["id"] for a in assertions if not a["pass"])
    return ChaosAssertionEvaluation(
        overall_pass=not failed,
        failed_ids=failed,
        assertion_count=len(assertions),
    )


@dataclass(frozen=True)
class MetricsSmokeScore:
    verdict: Literal["PASS", "WARN", "FAIL"]
    reasons: tuple[str, ...]
    no_data_detected: bool
    prometheus_reachable: bool
    grafana_reachable: bool


def score_metrics_smoke_report(report: dict[str, Any]) -> MetricsSmokeScore:
    """Fixture-based metrics smoke scoring — not live Prometheus/Grafana proof."""
    reasons: list[str] = []
    prom = report.get("prometheus", {}) if isinstance(report, dict) else {}
    grafana = report.get("grafana", {}) if isinstance(report, dict) else {}

    prom_error = prom.get("error")
    grafana_error = grafana.get("error") if isinstance(grafana, dict) else None

    prom_reachable = prom_error is None
    grafana_reachable = grafana_error is None

    active_targets = prom.get("targets_active")
    if prom_reachable and active_targets is None:
        active_targets = prom.get("active_targets")

    no_data = False
    if prom_reachable:
        if active_targets == 0:
            no_data = True
            reasons.append("prometheus has zero active targets")
        elif active_targets is None and prom.get("query_no_data"):
            no_data = True
            reasons.append("prometheus query returned no data")

    if not prom_reachable:
        reasons.append(f"prometheus unreachable: {prom_error}")
    if not grafana_reachable:
        reasons.append(f"grafana unreachable: {grafana_error}")

    if not prom_reachable and not grafana_reachable:
        return MetricsSmokeScore("FAIL", tuple(reasons), no_data, False, False)

    if no_data or (prom_reachable and not grafana_reachable):
        return MetricsSmokeScore(
            "WARN",
            tuple(reasons or ("partial monitoring visibility",)),
            no_data,
            prom_reachable,
            grafana_reachable,
        )

    if prom_reachable and grafana_reachable:
        return MetricsSmokeScore("PASS", tuple(reasons), False, True, True)

    return MetricsSmokeScore("FAIL", tuple(reasons or ("metrics smoke incomplete",)), no_data, prom_reachable, grafana_reachable)


@dataclass(frozen=True)
class DocsDriftFinding:
    category: str
    source: str
    detail: str


@dataclass(frozen=True)
class DocsDriftScanResult:
    missing_paths: tuple[str, ...]
    stale_todo_hooks: tuple[str, ...]
    findings: tuple[DocsDriftFinding, ...]

    @property
    def has_missing_paths(self) -> bool:
        return bool(self.missing_paths)


def resolve_repo_or_pack_path(path: str) -> Path:
    """Resolve repo-root or pack-relative references from docs/prompts."""
    normalized = path.replace("\\", "/").lstrip("/")
    if normalized.startswith("tools/test_pack/"):
        remainder = normalized.removeprefix("tools/test_pack/")
        if remainder in PACK_ROOT_FILES:
            return TEST_PACK_ROOT / remainder
        return resolve_pack_relative(remainder)
    if normalized.startswith(
        ("tools/", "scenarios/", "templates/", "runbooks/", "prompts/", "issue_pack/", "pack/", "infrastructure/")
    ):
        return resolve_pack_relative(normalized)
    return REPO_ROOT / normalized


def extract_pack_relative_paths(text: str) -> list[str]:
    """Extract pack-relative tool/doc paths from markdown or yaml text."""
    normalized_text = text.replace("\\", "/")
    seen: set[str] = set()
    ordered: list[str] = []
    for match in PACK_RELATIVE_PATH_PATTERN.finditer(normalized_text):
        path = match.group(0).replace("\\", "/")
        if path not in seen:
            seen.add(path)
            ordered.append(path)
    return ordered


def collect_stale_todo_hooks(text: str, *, label: str) -> list[str]:
    """Surface known stale TODO hooks — detection only, no auto-fix."""
    hooks: list[str] = []
    for pattern in STALE_TODO_HOOK_PATTERNS:
        if pattern.search(text):
            hooks.append(f"{label}: {pattern.pattern}")
    return hooks


def scan_paths_exist(
    paths: tuple[str, ...] | list[str],
    *,
    category: str,
    source: str,
) -> tuple[list[str], list[DocsDriftFinding]]:
    """Read-only path existence check for pack-relative references."""
    missing: list[str] = []
    findings: list[DocsDriftFinding] = []
    for rel in paths:
        candidate = resolve_repo_or_pack_path(rel)
        if not candidate.exists():
            missing.append(rel)
            findings.append(
                DocsDriftFinding(
                    category=category,
                    source=source,
                    detail=f"missing pack path: {rel}",
                )
            )
    return missing, findings


def scan_test_pack_docs_drift() -> DocsDriftScanResult:
    """Read-only docs/issue-pack drift scan — reports only, never mutates."""
    missing: list[str] = []
    findings: list[DocsDriftFinding] = []
    stale_hooks: list[str] = []

    readme_text = TEST_PACK_README.read_text(encoding="utf-8")
    for marker in README_FROZEN_STATUS_MARKERS:
        if marker not in readme_text:
            findings.append(
                DocsDriftFinding(
                    category="readme",
                    source="tools/test_pack/README.md",
                    detail=f"missing frozen-status marker: {marker!r}",
                )
            )

    path_groups: tuple[tuple[str, tuple[str, ...], str], ...] = (
        ("readme_quickstart", README_QUICKSTART_TOOL_PATHS, "tools/test_pack/README.md"),
        ("readme_extension", README_EXTENSION_TOOL_PATHS, "tools/test_pack/README.md"),
        ("issue_pack", ISSUE_PACK_PROMPT_REFS, "tools/test_pack/issue_pack/README.md"),
    )
    for category, paths, source in path_groups:
        gaps, group_findings = scan_paths_exist(paths, category=category, source=source)
        missing.extend(gaps)
        findings.extend(group_findings)

    issue_pack_readme = ISSUE_PACK_README.read_text(encoding="utf-8")
    stale_hooks.extend(collect_stale_todo_hooks(issue_pack_readme, label="issue_pack/README"))

    for issue_file in sorted((ISSUE_PACK_ROOT / "issues").glob("*.md")):
        issue_text = issue_file.read_text(encoding="utf-8")
        stale_hooks.extend(collect_stale_todo_hooks(issue_text, label=issue_file.name))

    for prompt_path in (PROMPT_IMPORT_TESTPACK, PROMPT_ISSUE_PACK):
        prompt_text = prompt_path.read_text(encoding="utf-8")
        stale_hooks.extend(collect_stale_todo_hooks(prompt_text, label=prompt_path.name))
        for rel in extract_pack_relative_paths(prompt_text):
            if rel in STALE_OPTIONAL_PACK_PATHS:
                continue
            candidate = resolve_repo_or_pack_path(rel)
            if not candidate.exists():
                missing.append(rel)
                findings.append(
                    DocsDriftFinding(
                        category="prompt",
                        source=str(prompt_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                        detail=f"missing pack path: {rel}",
                    )
                )

    catalog = load_scenario_catalog()
    for scenario in catalog.get("scenarios", []):
        for rel in scenario_artifact_paths(scenario):
            candidate = resolve_pack_relative(rel)
            if not candidate.exists():
                missing.append(rel)
                findings.append(
                    DocsDriftFinding(
                        category="scenario",
                        source=f"scenarios/catalog.yaml:{scenario.get('id')}",
                        detail=f"missing pack path: {rel}",
                    )
                )

    evidence_template = EVIDENCE_README_TEMPLATE.read_text(encoding="utf-8")
    stale_hooks.extend(
        collect_stale_todo_hooks(evidence_template, label="templates/evidence_pack_README.md")
    )

    return DocsDriftScanResult(
        missing_paths=tuple(dict.fromkeys(missing)),
        stale_todo_hooks=tuple(dict.fromkeys(stale_hooks)),
        findings=tuple(findings),
    )


def score_docs_drift_fixture(fixture: dict[str, Any]) -> DocsDriftScanResult:
    """Fixture-based docs drift scoring — mirrors scan semantics without repo writes."""
    missing: list[str] = []
    findings: list[DocsDriftFinding] = []
    stale_hooks: list[str] = []

    for doc in fixture.get("documents", []):
        label = str(doc.get("label", "fixture"))
        text = str(doc.get("text", ""))
        stale_hooks.extend(collect_stale_todo_hooks(text, label=label))
        for rel in doc.get("required_paths", []):
            if rel in doc.get("missing_paths", []):
                missing.append(rel)
                findings.append(
                    DocsDriftFinding(
                        category=str(doc.get("category", "fixture")),
                        source=label,
                        detail=f"missing pack path: {rel}",
                    )
                )

    for hook in fixture.get("expected_stale_hooks", []):
        if hook not in stale_hooks:
            findings.append(
                DocsDriftFinding(
                    category="stale_todo",
                    source="fixture",
                    detail=f"expected stale hook not visible: {hook}",
                )
            )

    return DocsDriftScanResult(
        missing_paths=tuple(missing),
        stale_todo_hooks=tuple(stale_hooks),
        findings=tuple(findings),
    )


def assert_drift_scanner_source_is_read_only(helper_source: str) -> list[str]:
    """Contract guard: drift helpers must not auto-fix docs or create issues."""
    violations: list[str] = []
    for pattern in NO_AUTO_FIX_FORBIDDEN_SOURCE_PATTERNS:
        if pattern.search(helper_source):
            violations.append(f"forbidden no-auto-fix pattern in helpers: {pattern.pattern!r}")
    return violations


def runtime_drill_operator_markers(script_text: str) -> dict[str, bool]:
    lowered = script_text.lower()
    return {
        "uses_docker_subprocess": "subprocess" in lowered and "docker" in lowered,
        "mentions_container_restart": "restart" in lowered and "cdb_" in script_text,
        "mentions_netem": "netem" in lowered,
        "requires_cdb_redis": CANONICAL_REDIS_CONTAINER in script_text,
    }
