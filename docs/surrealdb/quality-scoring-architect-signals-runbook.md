# Quality Scoring & Architect Signals — Runbook

**Wave 18 — Knowledge Quality Scoring & Architect Signals**  
Issues: #2171 #2172 #2173 #2174 #2175 #2176 #2177  
Parent: #2170 (Wave-18 anchor) · Epic: #1976

---

## 1. Overview

Wave 18 introduces two new read-only services to the SurrealDB Context Intelligence layer:

| Service | Purpose |
|---|---|
| **Knowledge Quality Scoring** (`quality_scoring.py`) | Score context bundles across 8 quality dimensions |
| **Architect Signals** (`architect_signals.py`) | Detect structural architecture signals from bundles |

Both services are:
- **Pure functions** — no DB access, no network, no SurrealDB SDK
- **Bundle-driven** — operate on in-memory JSON bundles only
- **Fail-closed** — missing/invalid input returns an error, never reads from DB
- **Read-only** — signal is recommendation, not authorization
- **No live-go** — LR Status remains `NO-GO` for live trading

---

## 2. Quality Scoring

### 2.1 Score Dimensions

| Dimension | What it measures |
|---|---|
| `coverage_score` | Fraction of sources with documentation AND tests |
| `freshness_score` | Currency of sources and decisions (stale findings, superseded decisions) |
| `evidence_score` | Strength and freshness of evidence items |
| `contradiction_score` | Inverse: proportion of open, unresolved contradictions |
| `dependency_confidence_score` | Confidence of dependency graph edges |
| `memory_trust_score` | Trust level of memory items |
| `decision_validity_score` | Fraction of decisions that are current (not superseded/invalidated) |
| `scope_risk_score` | Inverse: proportion of open scope drift findings |

### 2.2 Grade Bands

| Grade | Score Range | Meaning |
|---|---|---|
| `blocking` | 0.00 – 0.30 | Critical quality gap. Human-GO required before writes. |
| `watch` | 0.30 – 0.50 | Significant concerns. Review before acting. |
| `weak` | 0.50 – 0.70 | Below target. Improvement recommended. |
| `good` | 0.70 – 1.00 | Acceptable quality. Continue with normal process. |

**Blocking downgrade rule**: If any single dimension is `blocking`, the overall grade is capped at `watch` regardless of other dimension scores.

### 2.3 CLI Usage

```bash
# Score a bundle from file
python -m tools.surrealdb.quality_scoring_cli score-knowledge --input bundle.json

# Score and fail (exit code 1) if grade is weak or blocking
python -m tools.surrealdb.quality_scoring_cli score-knowledge --input bundle.json --fail-on-weak

# Show a single dimension score
python -m tools.surrealdb.quality_scoring_cli show-score --input bundle.json --dimension coverage_score

# Full quality report in Markdown
python -m tools.surrealdb.quality_scoring_cli report-quality --input bundle.json --format markdown

# JSON output
python -m tools.surrealdb.quality_scoring_cli report-quality --input bundle.json --format json
```

**Exit codes:**

| Code | Meaning |
|---|---|
| `0` | OK — all dimensions `good` or `weak` (or `--fail-on-weak` not set) |
| `1` | WEAK — weak or blocking grade detected when `--fail-on-weak` is set |
| `2` | ERROR — invalid input, unexpected error |
| `3` | NOT FOUND — bundle file not found |

### 2.4 MCP Tool: `cdb_context_quality_score`

**Required parameters:**
- `bundle` (dict): Quality scoring bundle

**Optional parameters:**
- `dimension` (str): Filter to a single dimension name
- `min_grade` (str): Filter to dimensions at or below this grade (`blocking`/`watch`/`weak`/`good`)
- `limit` (int): Maximum dimensions to return (default 100, max 500)
- `as_of` (str): Advisory ISO-8601 UTC timestamp

**Example call:**
```json
{
  "tool": "cdb_context_quality_score",
  "parameters": {
    "bundle": { "meta": {"scope_id": "...", "level": "system"}, "sources": [...] },
    "min_grade": "blocking"
  }
}
```

**Response:**
```json
{
  "tool": "cdb_context_quality_score",
  "schema_version": "quality-score-mcp/v1",
  "status": "ok",
  "scope_id": "...",
  "level": "system",
  "scored_at": "2026-05-06T12:00:00+00:00",
  "overall_score": 0.82,
  "overall_grade": "good",
  "blocking_dimensions": [],
  "watch_dimensions": [],
  "recommended_next_reads": [],
  "dimensions": [...],
  "guardrails": [...],
  "metadata": {"source": "in_memory", "read_only": true}
}
```

---

## 3. Architect Signals

### 3.1 Signal Types

| Signal Type | Severity | Triggered when |
|---|---|---|
| `stale_area` | `watch` | ≥ 2 open stale findings on the same path |
| `weakly_evidenced_decision` | `watch` | Decision has no strong/moderate evidence refs |
| `underdocumented_surface` | `watch` | Sources lack documentation |
| `undertested_surface` | `watch` | Sources lack tests |
| `high_dependency_risk` | `watch` | ≥ 50% of dependency edges have low/unknown confidence |
| `contradiction_hotspot` | `watch`/`blocking` | ≥ 2 open contradictions on same path (blocking if ≥ 4) |
| `scope_drift_hotspot` | `blocking` | ≥ 2 open scope drift findings on same path |
| `repeated_agent_confusion` | `watch` | Same path has both stale and contradiction findings |
| `redundant_docs` | `info` | Documentation sources outnumber code sources (heuristic) |
| `missing_owner` | `info` | Sources without owner/team/author metadata |
| `fragile_context_path` | `blocking` | Path appears in stale + contradiction + scope drift findings |

### 3.2 Severity Levels

| Severity | Action |
|---|---|
| `info` | Informational. No immediate action required. |
| `watch` | Review recommended before proceeding. |
| `blocking` | Stop writes. Human-GO required before action. |

### 3.3 MCP Tool: `cdb_context_architect_signals`

**Required parameters:**
- `bundle` (dict): Context bundle

**Optional parameters:**
- `signal_type` (str): Filter to a single signal type
- `min_severity` (str): Filter by minimum severity (`info`/`watch`/`blocking`)
- `limit` (int): Maximum signals to return (default 100, max 500)
- `as_of` (str): Advisory ISO-8601 UTC timestamp

**Example call:**
```json
{
  "tool": "cdb_context_architect_signals",
  "parameters": {
    "bundle": { "meta": {"scope_id": "...", "level": "system"}, "sources": [...] },
    "min_severity": "blocking"
  }
}
```

**Response:**
```json
{
  "tool": "cdb_context_architect_signals",
  "schema_version": "architect-signals-mcp/v1",
  "status": "ok",
  "scope_id": "...",
  "scanned_at": "2026-05-06T12:00:00+00:00",
  "total_signals": 3,
  "blocking_count": 1,
  "watch_count": 2,
  "signals": [
    {
      "signal_id": "abc123def456",
      "signal_type": "fragile_context_path",
      "severity": "blocking",
      "title": "1 path(s) have stale + contradiction + scope drift findings",
      "explanation": "...",
      "affected_paths": ["docs/operations/runbook.md"],
      "evidence_refs": [],
      "recommended_action": "Do not proceed with writes. Human-GO required.",
      "status": "open",
      "detected_by": "architect-signals/v1",
      "detected_at": "2026-05-06T12:00:00+00:00"
    }
  ],
  "guardrails": [...],
  "metadata": {"source": "in_memory", "read_only": true}
}
```

---

## 4. Bundle Format Reference

Both tools share the same bundle format:

```json
{
  "meta": {
    "scope_id": "unique-scope-id",
    "level": "artifact | domain | issue | system"
  },
  "sources": [
    {
      "source_path": "core/domain/models.py",
      "has_documentation": true,
      "has_tests": true,
      "status": "current",
      "file_type": "python",
      "owner": "trading-core"
    }
  ],
  "decisions": [
    {
      "decision_id": "dec-001",
      "status": "current | superseded | invalidated",
      "evidence_refs": ["ev-001"]
    }
  ],
  "evidence_items": [
    {
      "evidence_id": "ev-001",
      "strength": "strong | moderate | weak | none",
      "expired": false
    }
  ],
  "contradiction_findings": [
    {
      "contradiction_id": "c-001",
      "severity": "blocking | warning | info",
      "status": "open | resolved | false_positive | accepted_risk",
      "source_path": "docs/example.md"
    }
  ],
  "stale_findings": [
    {
      "stale_id": "s-001",
      "status": "stale | refreshed | accepted_risk | false_positive",
      "source_path": "docs/example.md",
      "reason": "Not reviewed in 60+ days"
    }
  ],
  "dependency_edges": [
    {
      "edge_id": "edge-001",
      "confidence": "high | medium | low | unknown",
      "source": "core/risk",
      "target": "core/domain"
    }
  ],
  "memory_items": [
    {
      "memory_id": "mem-001",
      "trust_level": "strong | acceptable | weak | blocked"
    }
  ],
  "scope_drift_findings": [
    {
      "drift_id": "drift-001",
      "severity": "blocking | warning | info",
      "status": "open | false_positive | accepted_risk",
      "source_path": "services/execution/service.py"
    }
  ]
}
```

---

## 5. Human Escalation Guide

| Condition | Required Action |
|---|---|
| `overall_grade == blocking` | Stop. Human-GO required before any write. |
| `fragile_context_path` signal detected | Stop writes to affected paths. Human-GO. |
| `scope_drift_hotspot` signal detected | Stop writes to affected area. Human-GO. |
| `contradiction_hotspot` with severity `blocking` | Resolve contradictions before proceeding. Human-GO. |
| Any signal `status == open` with `severity == blocking` | Escalate to human reviewer. |

**Accepted Risk Modelling:**  
Any finding or signal can be modelled as `accepted_risk` or `false_positive` by updating its `status` in the bundle before re-scoring. This does not bypass guardrails — it records the human decision to accept the risk.

---

## 6. Guardrails (All tools enforce these)

1. Quality Score is signal, not authorization.
2. Architect Signal is recommendation, not command.
3. No automatic issue creation.
4. No auto-fix. No auto-write.
5. No Live-Readiness-Go.
6. No Echtgeld-Go.
7. Human-GO required for any action after blocking score or signal.

---

## 7. File Locations

| File | Purpose |
|---|---|
| `tools/surrealdb/quality_scoring.py` | Quality Scoring Service v1 |
| `tools/surrealdb/quality_scoring_cli.py` | Quality Scoring CLI |
| `tools/mcp/quality_scoring_tools.py` | MCP adapter for quality score |
| `tools/surrealdb/architect_signals.py` | Architect Signal Service v1 |
| `tools/mcp/architect_signal_tools.py` | MCP adapter for architect signals |
| `tests/unit/surrealdb/test_quality_scoring.py` | Quality scoring tests |
| `tests/unit/tools/mcp/test_quality_scoring_tools.py` | MCP quality scoring tests |
| `tests/fixtures/surrealdb/quality_scoring/sample_bundle.json` | Sample bundle fixture |
| `docs/surrealdb/quality-scoring-architect-signals-runbook.md` | This file |
| `docs/surrealdb/context-wave18-completion-gates.md` | Wave-18 completion gates |
