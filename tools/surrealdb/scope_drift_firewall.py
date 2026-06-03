"""Scope Drift Firewall Service v1 — side-effect-free domain component.

Issues:
    #2163 — [SURREALDB][CONTEXT][SCOPE-FIREWALL] Implement scope drift firewall service v1
    Parent: #2162 (Wave-17 anchor)
    Epic: #1976

Scope:
    Implements a minimal, deterministic scope-drift-firewall service that works
    purely on in-memory records (input bundles as dicts). No DB access. No
    SurrealDB SDK. No MCP. No networking. No writes. No auto-fix. No live-go.

    Detects scope drift for:
        path_out_of_scope, domain_out_of_scope, issue_out_of_scope,
        parked_topic_activated, runtime_surface_touched,
        trading_surface_touched, unexpected_dependency_expansion,
        unauthorized_write_intent, missing_human_go

Guardrails:
    - Detection only: never implies approval, live-go, or decision authority.
    - Blocking findings are surfaced explicitly but do NOT grant permission to act.
    - No write, no mutation, no GitHub/runtime write from this module.
    - No direct wall-clock calls or random UUID generation (use core.utils.clock).
    - LR status remains NO-GO for live trading.
    - Scope Drift Detection is signal, not authorization.
    - Human-GO required for any write after blocking scope drift.
"""

from __future__ import annotations

import fnmatch
import hashlib
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.utils.clock import utcnow as cdb_utcnow

SCHEMA_VERSION = "scope-drift-firewall/v1"
TOOL_NAME = "scope_drift_firewall"
DETECTED_BY = "scope-drift-firewall/v1"

DRIFT_TYPES = frozenset(
    {
        "path_out_of_scope",
        "domain_out_of_scope",
        "issue_out_of_scope",
        "parked_topic_activated",
        "runtime_surface_touched",
        "trading_surface_touched",
        "unexpected_dependency_expansion",
        "unauthorized_write_intent",
        "missing_human_go",
    }
)

SEVERITY_LEVELS = ("info", "warning", "blocking")

STATUS_VALUES = frozenset(
    {
        "open",
        "acknowledged",
        "false_positive",
        "accepted_risk",
        "resolved",
    }
)

REQUIRED_ACTIONS = frozenset({"stop", "review", "split_scope", "request_go"})

GUARDRAILS: tuple[str, ...] = (
    "Scope Drift Detection is signal, not authorization.",
    "No auto-fix. No auto-write.",
    "No Live-Readiness-Go.",
    "No Echtgeld-Go.",
    "Human-GO required for any write after blocking scope drift.",
)

# Surface types that indicate runtime/service scope
_RUNTIME_SURFACE_TYPES = frozenset({"runtime", "service"})

# Surface types that indicate trading scope
_TRADING_SURFACE_TYPES = frozenset({"trading"})

# Path prefixes that indicate trading scope (in addition to surface_type check)
_TRADING_PATH_PREFIXES = (
    "services/risk/",
    "services/execution/",
)

# Known parked/dangerous path patterns that must not be activated outside explicit GO
_PARKED_PATH_PATTERNS = (
    "services/risk/",
    "services/execution/",
    "governance/DELIVERY_APPROVED",
    "core/safety/",
    "infrastructure/database/",
    "infrastructure/compose/",
)

# Operation modes that imply write intent → require human_go_token
_WRITE_LIKE_MODES = frozenset({"write", "plan_write", "commit", "push", "create_pr"})

# Default max artifact count before unexpected_dependency_expansion triggers
_DEFAULT_MAX_ARTIFACT_COUNT = 20

# Write-intent keywords in generated_findings content
_WRITE_INTENT_KEYWORDS = (
    "write ",
    "create file",
    "modify file",
    "delete file",
    "push to",
    "commit ",
    "open pr",
    "create pr",
    "git push",
    "git commit",
)


class ScopeDriftFirewallError(ValueError):
    """Raised when scope drift firewall inputs are invalid or unsafe."""


# ── Data Models ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ScopeDriftFinding:
    """A single detected scope drift finding.

    Output contract — all fields guaranteed to be present:
        drift_id                deterministic, stable identifier (SHA256 prefix)
        drift_type              one of DRIFT_TYPES
        severity                info | warning | blocking
        allowed_scope           human-readable description of what was allowed
        observed_scope          human-readable description of what was observed
        affected_artifacts      tuple of affected artifact paths/IDs
        required_action         stop | review | split_scope | request_go
        human_go_required       bool — true iff severity=blocking
        stop_conditions         tuple of stop conditions (non-empty for blocking)
        recommended_next_reads  tuple of suggested files/docs to review
        detected_by             str — service/version that detected this
        detected_at             ISO-8601 UTC string — via cdb_utcnow (not wall-clock)
        status                  one of STATUS_VALUES
    """

    drift_id: str
    drift_type: str
    severity: str
    allowed_scope: str
    observed_scope: str
    affected_artifacts: tuple[str, ...]
    required_action: str
    human_go_required: bool
    stop_conditions: tuple[str, ...]
    recommended_next_reads: tuple[str, ...]
    detected_by: str
    detected_at: str
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "drift_id": self.drift_id,
            "drift_type": self.drift_type,
            "severity": self.severity,
            "allowed_scope": self.allowed_scope,
            "observed_scope": self.observed_scope,
            "affected_artifacts": list(self.affected_artifacts),
            "required_action": self.required_action,
            "human_go_required": self.human_go_required,
            "stop_conditions": list(self.stop_conditions),
            "recommended_next_reads": list(self.recommended_next_reads),
            "detected_by": self.detected_by,
            "detected_at": self.detected_at,
            "status": self.status,
        }


@dataclass(frozen=True)
class ScopeDriftScanResult:
    """Result of a full scope drift firewall scan run."""

    tool: str
    schema_version: str
    status: str
    scanned_at: str
    blocking_count: int
    findings: tuple[ScopeDriftFinding, ...]
    guardrails: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        severity_summary: dict[str, int] = {level: 0 for level in SEVERITY_LEVELS}
        for f in self.findings:
            if f.severity in severity_summary:
                severity_summary[f.severity] += 1

        return {
            "tool": self.tool,
            "schema_version": self.schema_version,
            "status": self.status,
            "scanned_at": self.scanned_at,
            "total_count": len(self.findings),
            "blocking_count": self.blocking_count,
            "severity_summary": severity_summary,
            "findings": [f.to_dict() for f in self.findings],
            "guardrails": list(self.guardrails),
        }


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_drift_id(drift_type: str, observed_scope: str, affected: str) -> str:
    """Generate a deterministic, stable drift finding ID.

    Uses SHA256 of the canonical string (drift_type|observed_scope|affected).
    No random UUID generation — guardrails-compliant.
    """
    raw = f"{drift_type}|{observed_scope}|{affected}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text if text else None
    return str(value).strip() or None


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _declared_scope_mapping(bundle: Mapping[str, Any]) -> Mapping[str, Any]:
    """Normalize declared_scope for rule evaluation (fail-closed, no AttributeError).

    Operator/benchmark bundles may pass a plain scope label string instead of a
    structured object. A non-empty string means "label only" with no path/issue
    constraints — rules that require target_paths or allowed_domains stay inactive.
    """
    raw = bundle.get("declared_scope")
    if raw is None:
        return {}
    if isinstance(raw, Mapping):
        return raw
    if isinstance(raw, str):
        return {}
    raise ScopeDriftFirewallError(
        "declared_scope must be a mapping/object or scope label string, "
        f"got {type(raw).__name__}"
    )


def _meta_mapping(bundle: Mapping[str, Any]) -> Mapping[str, Any]:
    """Normalize meta to a mapping; ignore non-mapping values (no path constraints)."""
    raw = bundle.get("meta")
    if raw is None:
        return {}
    if isinstance(raw, Mapping):
        return raw
    return {}


def _make_finding(
    *,
    drift_type: str,
    severity: str,
    allowed_scope: str,
    observed_scope: str,
    affected_artifacts: Sequence[str] = (),
    required_action: str,
    stop_conditions: Sequence[str] = (),
    recommended_next_reads: Sequence[str] = (),
    detected_at: str,
    status: str = "open",
) -> ScopeDriftFinding:
    affected_str = "; ".join(affected_artifacts) if affected_artifacts else observed_scope
    did = _make_drift_id(drift_type, observed_scope, affected_str)
    human_go_required = severity == "blocking"
    _default_reads = ("AGENTS.md", "docs/runbooks/CONTROL_REGISTER.md")
    merged_reads: list[str] = list(recommended_next_reads)
    for r in _default_reads:
        if r not in merged_reads:
            merged_reads.append(r)
    return ScopeDriftFinding(
        drift_id=did,
        drift_type=drift_type,
        severity=severity,
        allowed_scope=allowed_scope,
        observed_scope=observed_scope,
        affected_artifacts=tuple(affected_artifacts),
        required_action=required_action,
        human_go_required=human_go_required,
        stop_conditions=tuple(stop_conditions),
        recommended_next_reads=tuple(merged_reads),
        detected_by=DETECTED_BY,
        detected_at=detected_at,
        status=status,
    )


def _path_is_within_scope(path: str, target_paths: list[str]) -> bool:
    """Return True if path starts with any of the declared target_paths.

    Requires a directory-boundary match to avoid sibling-prefix false negatives:
    e.g. 'tools/surrealdb_extra/f.py' must NOT match target 'tools/surrealdb'.

    Supports glob patterns (schema: target_paths accepts "glob patterns"):
    e.g. 'tools/surrealdb/*.py' matches 'tools/surrealdb/scope_drift_firewall.py'.
    """
    if not target_paths:
        return True  # no constraint declared → not a violation
    for prefix in target_paths:
        norm = prefix.rstrip("/")
        if path == norm or path.startswith(norm + "/"):
            return True
        # Glob pattern support (schema documents target_paths as "glob patterns")
        if any(c in prefix for c in ("*", "?", "[")):
            if fnmatch.fnmatch(path, prefix):
                return True
    return False


# ── Detection Rules ───────────────────────────────────────────────────────────


def _rule_path_out_of_scope(
    bundle: Mapping[str, Any],
    detected_at: str,
) -> list[ScopeDriftFinding]:
    """Rule: touched artifact path is outside declared_scope.target_paths.

    Input contract:
        declared_scope.target_paths: list[str]  — allowed path prefixes
        touched_artifacts[].path: str
    """
    findings: list[ScopeDriftFinding] = []
    declared_scope = _declared_scope_mapping(bundle)
    target_paths = _as_list(declared_scope.get("target_paths"))
    touched = _as_list(bundle.get("touched_artifacts"))

    if not target_paths:
        return findings  # no path constraint declared — not a violation

    for artifact in touched:
        if not artifact:
            continue
        path = _as_str(artifact.get("path"))
        if not path:
            continue
        if not _path_is_within_scope(path, target_paths):
            allowed_scope_str = ", ".join(target_paths)
            findings.append(
                _make_finding(
                    drift_type="path_out_of_scope",
                    severity="blocking",
                    allowed_scope=f"Paths under: {allowed_scope_str}",
                    observed_scope=path,
                    affected_artifacts=[path],
                    required_action="stop",
                    stop_conditions=[
                        f"Path '{path}' is outside declared scope. Do not proceed until scope is clarified.",
                        "No writes outside declared target_paths without explicit Human-GO.",
                    ],
                    recommended_next_reads=[
                        "knowledge/governance/CDB_AGENT_POLICY.md",
                    ],
                    detected_at=detected_at,
                )
            )
    return findings


def _rule_domain_out_of_scope(
    bundle: Mapping[str, Any],
    detected_at: str,
) -> list[ScopeDriftFinding]:
    """Rule: artifact surface_type is not in declared_scope.allowed_domains.

    Only fires when declared_scope.allowed_domains is explicitly provided.

    Input contract:
        declared_scope.allowed_domains: list[str]  — optional allowed surface types
        touched_artifacts[].surface_type: str
    """
    findings: list[ScopeDriftFinding] = []
    declared_scope = _declared_scope_mapping(bundle)
    allowed_domains = _as_list(declared_scope.get("allowed_domains"))
    touched = _as_list(bundle.get("touched_artifacts"))

    if not allowed_domains:
        return findings  # no domain constraint declared — not a violation

    allowed_set = frozenset(d.lower() for d in allowed_domains if d)

    for artifact in touched:
        if not artifact:
            continue
        surface_type = _as_str(artifact.get("surface_type"))
        if not surface_type:
            continue
        if surface_type.lower() not in allowed_set:
            path = _as_str(artifact.get("path")) or "(unknown path)"
            findings.append(
                _make_finding(
                    drift_type="domain_out_of_scope",
                    severity="warning",
                    allowed_scope=f"Domains: {', '.join(allowed_domains)}",
                    observed_scope=f"surface_type='{surface_type}' for path='{path}'",
                    affected_artifacts=[path],
                    required_action="review",
                    stop_conditions=[],
                    recommended_next_reads=[
                        "knowledge/governance/CDB_AGENT_POLICY.md",
                    ],
                    detected_at=detected_at,
                )
            )
    return findings


def _rule_issue_out_of_scope(
    bundle: Mapping[str, Any],
    detected_at: str,
) -> list[ScopeDriftFinding]:
    """Rule: issue_refs contains an issue not related to target_issue or allowed_issues.

    Input contract:
        declared_scope.target_issue: str  — primary issue (e.g. "2163")
        declared_scope.allowed_issues: list[str]  — optional additional allowed issues
        issue_refs[].issue_id: str
        issue_refs[].state: str
        issue_refs[].label: str  — optional
    """
    findings: list[ScopeDriftFinding] = []
    declared_scope = _declared_scope_mapping(bundle)
    target_issue = _as_str(declared_scope.get("target_issue"))
    allowed_issues_raw = _as_list(declared_scope.get("allowed_issues"))
    issue_refs = _as_list(bundle.get("issue_refs"))

    if not target_issue:
        return findings  # no target issue declared — not a violation

    allowed_set: set[str] = {target_issue}
    for iss in allowed_issues_raw:
        s = _as_str(iss)
        if s:
            allowed_set.add(s)

    for ref in issue_refs:
        if not ref:
            continue
        issue_id = _as_str(ref.get("issue_id"))
        if not issue_id:
            continue
        if issue_id not in allowed_set:
            findings.append(
                _make_finding(
                    drift_type="issue_out_of_scope",
                    severity="warning",
                    allowed_scope=f"Issues: {', '.join(sorted(allowed_set))}",
                    observed_scope=f"issue #{issue_id}",
                    affected_artifacts=[f"issue#{issue_id}"],
                    required_action="review",
                    stop_conditions=[],
                    recommended_next_reads=[
                        "knowledge/governance/CDB_AGENT_POLICY.md",
                    ],
                    detected_at=detected_at,
                )
            )
    return findings


def _rule_parked_topic_activated(
    bundle: Mapping[str, Any],
    detected_at: str,
) -> list[ScopeDriftFinding]:
    """Rule: a touched artifact path matches a known parked/dangerous surface.

    Checks against both the hardcoded _PARKED_PATH_PATTERNS and the
    bundle's forbidden_surfaces list.

    Input contract:
        touched_artifacts[].path: str
        forbidden_surfaces[].surface: str
        forbidden_surfaces[].reason: str
    """
    findings: list[ScopeDriftFinding] = []
    touched = _as_list(bundle.get("touched_artifacts"))
    forbidden_surfaces = _as_list(bundle.get("forbidden_surfaces"))

    # Build set of forbidden surface prefixes from bundle
    bundle_forbidden: list[tuple[str, str]] = []
    for fs in forbidden_surfaces:
        if not fs:
            continue
        surface = _as_str(fs.get("surface"))
        reason = _as_str(fs.get("reason")) or "declared forbidden surface"
        if surface:
            bundle_forbidden.append((surface, reason))

    for artifact in touched:
        if not artifact:
            continue
        path = _as_str(artifact.get("path"))
        if not path:
            continue

        # Check hardcoded parked patterns
        for pattern in _PARKED_PATH_PATTERNS:
            if path == pattern or path.startswith(pattern):
                findings.append(
                    _make_finding(
                        drift_type="parked_topic_activated",
                        severity="blocking",
                        allowed_scope="Paths outside known-parked surfaces",
                        observed_scope=f"path='{path}' matches parked pattern '{pattern}'",
                        affected_artifacts=[path],
                        required_action="stop",
                        stop_conditions=[
                            f"Path '{path}' activates a known-parked surface ('{pattern}'). "
                            "Human-GO required before proceeding.",
                        ],
                        recommended_next_reads=[
                            "knowledge/governance/CDB_AGENT_POLICY.md",
                            "knowledge/governance/SYSTEM_INVARIANTS.md",
                        ],
                        detected_at=detected_at,
                    )
                )
                break  # one finding per artifact

        # Check bundle-declared forbidden surfaces
        for surface, reason in bundle_forbidden:
            if path == surface or path.startswith(surface.rstrip("/") + "/"):
                # Avoid duplicate if already flagged by hardcoded pattern
                already = any(
                    f.drift_type == "parked_topic_activated"
                    and path in f.affected_artifacts
                    for f in findings
                )
                if not already:
                    findings.append(
                        _make_finding(
                            drift_type="parked_topic_activated",
                            severity="blocking",
                            allowed_scope="Paths outside declared forbidden surfaces",
                            observed_scope=f"path='{path}' matches forbidden surface '{surface}'",
                            affected_artifacts=[path],
                            required_action="stop",
                            stop_conditions=[
                                f"Path '{path}' activates declared forbidden surface: {reason}. "
                                "Human-GO required before proceeding.",
                            ],
                            recommended_next_reads=[
                                "knowledge/governance/CDB_AGENT_POLICY.md",
                            ],
                            detected_at=detected_at,
                        )
                    )
                break

    return findings


def _rule_runtime_surface_touched(
    bundle: Mapping[str, Any],
    detected_at: str,
) -> list[ScopeDriftFinding]:
    """Rule: a touched artifact has surface_type == 'runtime' or 'service'.

    Input contract:
        touched_artifacts[].path: str
        touched_artifacts[].surface_type: str
    """
    findings: list[ScopeDriftFinding] = []
    touched = _as_list(bundle.get("touched_artifacts"))

    for artifact in touched:
        if not artifact:
            continue
        surface_type = _as_str(artifact.get("surface_type"))
        if not surface_type:
            continue
        if surface_type.lower() in _RUNTIME_SURFACE_TYPES:
            path = _as_str(artifact.get("path")) or "(unknown path)"
            findings.append(
                _make_finding(
                    drift_type="runtime_surface_touched",
                    severity="blocking",
                    allowed_scope="Non-runtime, non-service surfaces",
                    observed_scope=f"surface_type='{surface_type}' for path='{path}'",
                    affected_artifacts=[path],
                    required_action="stop",
                    stop_conditions=[
                        f"Runtime surface '{surface_type}' was touched at path '{path}'. "
                        "Runtime surfaces require explicit Human-GO.",
                        "No changes to runtime or service surfaces without written authorization.",
                    ],
                    recommended_next_reads=[
                        "knowledge/governance/SYSTEM_INVARIANTS.md",
                        "knowledge/governance/CDB_AGENT_POLICY.md",
                    ],
                    detected_at=detected_at,
                )
            )
    return findings


def _rule_trading_surface_touched(
    bundle: Mapping[str, Any],
    detected_at: str,
) -> list[ScopeDriftFinding]:
    """Rule: a touched artifact is on the trading surface.

    Triggers on surface_type == 'trading' OR path starting with
    services/risk/ or services/execution/.

    Input contract:
        touched_artifacts[].path: str
        touched_artifacts[].surface_type: str
    """
    findings: list[ScopeDriftFinding] = []
    touched = _as_list(bundle.get("touched_artifacts"))

    for artifact in touched:
        if not artifact:
            continue
        surface_type = _as_str(artifact.get("surface_type")) or ""
        path = _as_str(artifact.get("path")) or ""

        is_trading_surface = surface_type.lower() in _TRADING_SURFACE_TYPES
        is_trading_path = any(path.startswith(p) for p in _TRADING_PATH_PREFIXES)

        if is_trading_surface or is_trading_path:
            artifact_ref = path or surface_type or "(unknown)"
            findings.append(
                _make_finding(
                    drift_type="trading_surface_touched",
                    severity="blocking",
                    allowed_scope="Non-trading surfaces and paths",
                    observed_scope=(
                        f"surface_type='{surface_type}', path='{path}'"
                        if path
                        else f"surface_type='{surface_type}'"
                    ),
                    affected_artifacts=[artifact_ref],
                    required_action="stop",
                    stop_conditions=[
                        "Trading surface touched. LR status is NO-GO. No changes to trading surfaces (risk, execution) without Human-GO.",
                        "Board stage 'trade-capable' is NOT a live-go.",
                    ],
                    recommended_next_reads=[
                        "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
                        "knowledge/governance/SYSTEM_INVARIANTS.md",
                        "knowledge/governance/CDB_AGENT_POLICY.md",
                    ],
                    detected_at=detected_at,
                )
            )
    return findings


def _rule_unexpected_dependency_expansion(
    bundle: Mapping[str, Any],
    detected_at: str,
) -> list[ScopeDriftFinding]:
    """Rule: touched_artifacts count significantly exceeds declared scope.

    Fires when:
        len(touched_artifacts) > declared_scope.max_artifact_count
    or
        len(touched_artifacts) > _DEFAULT_MAX_ARTIFACT_COUNT (when max not declared)
        AND target_paths is declared (i.e., there is an explicit scope)

    Input contract:
        declared_scope.max_artifact_count: int  — optional
        declared_scope.target_paths: list[str]  — optional
        touched_artifacts: list[dict]
    """
    findings: list[ScopeDriftFinding] = []
    declared_scope = _declared_scope_mapping(bundle)
    touched = _as_list(bundle.get("touched_artifacts"))
    target_paths = _as_list(declared_scope.get("target_paths"))

    raw_max = declared_scope.get("max_artifact_count")
    try:
        max_count = int(raw_max) if raw_max is not None else None
    except (TypeError, ValueError):
        max_count = None

    effective_max: int | None = None
    if max_count is not None:
        effective_max = max_count
    elif target_paths:
        # Use default threshold only when explicit path scope is declared
        effective_max = _DEFAULT_MAX_ARTIFACT_COUNT

    if effective_max is None:
        return findings  # no constraint basis

    artifact_count = len([a for a in touched if a])
    if artifact_count > effective_max:
        paths = [
            _as_str(a.get("path")) or "(no-path)"
            for a in touched
            if a
        ]
        findings.append(
            _make_finding(
                drift_type="unexpected_dependency_expansion",
                severity="warning",
                allowed_scope=f"At most {effective_max} artifacts",
                observed_scope=f"{artifact_count} artifacts touched",
                affected_artifacts=paths[:10],  # cap to keep output manageable
                required_action="split_scope",
                stop_conditions=[],
                recommended_next_reads=[
                    "knowledge/governance/CDB_AGENT_POLICY.md",
                ],
                detected_at=detected_at,
            )
        )
    return findings


def _rule_unauthorized_write_intent(
    bundle: Mapping[str, Any],
    detected_at: str,
) -> list[ScopeDriftFinding]:
    """Rule: generated_findings contains write-intent without human_go_token.

    Triggers when:
        generated_findings[].write_intent == True AND human_go_token is falsy
    or
        generated_findings[].content contains write-intent keywords AND human_go_token is falsy

    Input contract:
        generated_findings[].type: str
        generated_findings[].content: str
        generated_findings[].source: str
        generated_findings[].write_intent: bool  — optional, explicit flag
        generated_findings[].human_go_token: str | None  — present when GO was given
    """
    findings: list[ScopeDriftFinding] = []
    generated = _as_list(bundle.get("generated_findings"))

    for item in generated:
        if not item:
            continue
        write_intent_flag = item.get("write_intent", False)
        human_go_token = _as_str(item.get("human_go_token"))
        content = (_as_str(item.get("content")) or "").lower()
        source = _as_str(item.get("source")) or "unknown"
        finding_type = _as_str(item.get("type")) or "unknown"

        has_keyword = any(kw in content for kw in _WRITE_INTENT_KEYWORDS)
        is_write_intent = bool(write_intent_flag) or has_keyword
        has_go = bool(human_go_token)

        if is_write_intent and not has_go:
            snippet = content[:80] if content else "(no content)"
            findings.append(
                _make_finding(
                    drift_type="unauthorized_write_intent",
                    severity="blocking",
                    allowed_scope="Write intent only when human_go_token is present",
                    observed_scope=(
                        f"type='{finding_type}', source='{source}', content='{snippet}...'"
                    ),
                    affected_artifacts=[f"finding:{finding_type}:{source}"],
                    required_action="stop",
                    stop_conditions=[
                        "Write intent detected without Human-GO token. Stop immediately.",
                        "No writes, commits, or pushes without explicit Human-GO.",
                    ],
                    recommended_next_reads=[
                        "knowledge/governance/CDB_AGENT_POLICY.md",
                        "knowledge/governance/CDB_CONSTITUTION.md",
                    ],
                    detected_at=detected_at,
                )
            )
    return findings


def _rule_missing_human_go(
    bundle: Mapping[str, Any],
    detected_at: str,
) -> list[ScopeDriftFinding]:
    """Rule: operation_mode is write-like but no human_go_token present in bundle.

    Input contract:
        meta.operation_mode: str  — optional; one of _WRITE_LIKE_MODES → requires GO
        meta.human_go_token: str | None  — explicit GO token
    """
    findings: list[ScopeDriftFinding] = []
    meta = _meta_mapping(bundle)
    operation_mode = _as_str(meta.get("operation_mode")) or ""
    human_go_token = _as_str(meta.get("human_go_token"))

    _mode = operation_mode.lower()
    if _mode not in _WRITE_LIKE_MODES and not any(
        _mode.startswith(w) for w in _WRITE_LIKE_MODES
    ):
        return findings

    if bool(human_go_token):
        return findings

    findings.append(
        _make_finding(
            drift_type="missing_human_go",
            severity="blocking",
            allowed_scope=f"Write-like operations ({', '.join(sorted(_WRITE_LIKE_MODES))}) only with human_go_token",
            observed_scope=f"operation_mode='{operation_mode}', human_go_token=None",
            affected_artifacts=[f"operation:{operation_mode}"],
            required_action="request_go",
            stop_conditions=[
                f"Operation mode '{operation_mode}' requires explicit Human-GO. "
                "Set meta.human_go_token before proceeding.",
            ],
            recommended_next_reads=[
                "knowledge/governance/CDB_AGENT_POLICY.md",
                "knowledge/governance/CDB_CONSTITUTION.md",
            ],
            detected_at=detected_at,
        )
    )
    return findings


# ── Public API ────────────────────────────────────────────────────────────────


def scan_scope_drift_v1(
    bundle: Mapping[str, Any],
    as_of: str | None = None,
) -> ScopeDriftScanResult:
    """Run all scope drift detection rules on the provided input bundle.

    This is the primary public entry point. Read-only. No writes. No network.
    No DB access. No GitHub calls. No auto-fix. No auto-repair.

    Args:
        bundle:  Dict of input records describing declared scope, touched
                 artifacts, issue refs, generated findings, and forbidden
                 surfaces. Unknown keys are ignored.
        as_of:   Optional ISO-8601 UTC string representing the reference time.
                 Defaults to cdb_utcnow().isoformat().

    Returns:
        ScopeDriftScanResult with all findings, blocking_count, severity_summary,
        guardrails, and metadata.

    Guardrails:
        - No write operations anywhere in this call chain.
        - All timestamps via cdb_utcnow (clock-injected, not wall-clock).
        - No random UUID generation — IDs are SHA256-based and deterministic.
        - Blocking findings are surfaced but grant no action authority.
        - LR status remains NO-GO for live trading.
        - Scope Drift Detection is signal, not authorization.
        - Human-GO required for any write after blocking scope drift.
    """
    if not isinstance(bundle, Mapping):
        raise ScopeDriftFirewallError(
            f"bundle must be a Mapping, got {type(bundle).__name__}"
        )

    resolved_as_of: str = as_of if as_of is not None else cdb_utcnow().isoformat()
    detected_at = resolved_as_of

    all_findings: list[ScopeDriftFinding] = []

    all_findings.extend(_rule_path_out_of_scope(bundle, detected_at))
    all_findings.extend(_rule_domain_out_of_scope(bundle, detected_at))
    all_findings.extend(_rule_issue_out_of_scope(bundle, detected_at))
    all_findings.extend(_rule_parked_topic_activated(bundle, detected_at))
    all_findings.extend(_rule_runtime_surface_touched(bundle, detected_at))
    all_findings.extend(_rule_trading_surface_touched(bundle, detected_at))
    all_findings.extend(_rule_unexpected_dependency_expansion(bundle, detected_at))
    all_findings.extend(_rule_unauthorized_write_intent(bundle, detected_at))
    all_findings.extend(_rule_missing_human_go(bundle, detected_at))

    blocking_count = sum(1 for f in all_findings if f.human_go_required)
    overall_status = "blocked_scope_drift" if blocking_count > 0 else "ok"

    return ScopeDriftScanResult(
        tool=TOOL_NAME,
        schema_version=SCHEMA_VERSION,
        status=overall_status,
        scanned_at=resolved_as_of,
        blocking_count=blocking_count,
        findings=tuple(all_findings),
        guardrails=GUARDRAILS,
    )
