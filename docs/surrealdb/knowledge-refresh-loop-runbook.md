# Knowledge Refresh Loop Runbook

**Status:** MVP read-only closure slice  
**Authority:** Issue [#2717](https://github.com/jannekbuengener/Claire_de_Binare/issues/2717) / Epic [#1976](https://github.com/jannekbuengener/Claire_de_Binare/issues/1976)  
**Contract:** [`knowledge-refresh-loop-contract-v1.md`](knowledge-refresh-loop-contract-v1.md)

**LR-Status: NO-GO** — this runbook covers read-only reporting only.  
**Board Stage: trade-capable** — orthogonal to LR; no live capital.

---

## 1. Purpose

Operators and agents use the Knowledge Refresh Loop Report to see consolidated
refresh candidates across stale scan, refresh plan, quality, architect signals,
and optional Agent OS readiness — without triggering any write path.

Detection and classification are **signal, not authorization**.

---

## 2. Artefacts

| Artefact | Path |
|---|---|
| Orchestrator | `tools/surrealdb/knowledge_refresh_report.py` |
| CLI | `tools/surrealdb/knowledge_refresh_cli.py` |
| Fixture | `tests/fixtures/surrealdb/knowledge_refresh/sample_bundle.json` |
| Unit tests | `tests/unit/surrealdb/test_knowledge_refresh_report.py` |
| Contract | `docs/surrealdb/knowledge-refresh-loop-contract-v1.md` |

---

## 3. Operator Commands

### JSON report (stdout)

```bash
python -m tools.surrealdb.knowledge_refresh_cli report-knowledge-refresh \
  --input tests/fixtures/surrealdb/knowledge_refresh/sample_bundle.json \
  --format json \
  --as-of 2026-05-06T12:00:00+00:00
```

### Markdown report (stdout)

```bash
python -m tools.surrealdb.knowledge_refresh_cli report-knowledge-refresh \
  --input tests/fixtures/surrealdb/knowledge_refresh/sample_bundle.json \
  --format markdown \
  --as-of 2026-05-06T12:00:00+00:00
```

### Omit optional readiness summary

```bash
python -m tools.surrealdb.knowledge_refresh_cli report-knowledge-refresh \
  --input tests/fixtures/surrealdb/knowledge_refresh/sample_bundle.json \
  --no-readiness
```

### Programmatic use

```python
from tools.surrealdb.knowledge_refresh_report import generate_knowledge_refresh_report_v1

report = generate_knowledge_refresh_report_v1(bundle, as_of="2026-05-06T12:00:00+00:00")
print(report.to_json())
print(report.to_markdown())
```

---

## 4. Interpreting Classifications

| Classification | Operator action |
|---|---|
| `refresh_required` | Review and refresh content; canon paths still require human review |
| `archive_candidate` | Non-canon delete signal — propose archive only after human review |
| `needs_issue_proposal` | Review embedded text proposal; open GitHub issue manually if warranted |
| `stale_but_accepted` | Known/accepted drift — no automatic action |
| `orphan_candidate` | Investigate ownership and references |
| `canon_protected` | Treat as governance-critical; never auto-delete/archive |
| `no_action` | Informational only |

All items carry `write_authorized=false`. The refresh plan summary also
states `write_authorized=false`.

---

## 5. Issue Proposals

When classification is `needs_issue_proposal`, the report includes a
**text-only** `issue_proposal` block. The tool does **not** call GitHub.
Operators copy/adapt the proposal and open issues manually under epic #1976.

---

## 6. Validation

```bash
pytest tests/unit/surrealdb/test_knowledge_refresh_report.py -q
ruff check tools/surrealdb/knowledge_refresh_report.py tools/surrealdb/knowledge_refresh_cli.py
```

Expected: all tests pass; ruff clean; no network/DB activity in pure-report path.

---

## 7. Guardrails

- Read-only first; Git/repo remains source of truth.
- `CURRENT_STATUS.md` is a ledger, not live truth.
- Board stage `trade-capable` is not a live-go.
- Live-Readiness remains NO-GO.
- No documentation deletion without separate Human-GO.
- No memory writes without separate Human-GO (#2606).
- No CI scheduler or MCP exposure in v1.

---

## 8. Out of Scope

| Item | Notes |
|---|---|
| #2689 Gordon/Docker AI cleanup | Separate doc decommission track |
| #2606 memory persistence | Not required for read-only MVP |
| CI automation (#2202 follow-up) | Future slice |
| DB-backed default bundle | Depends on #2603 maturity |

---

## 9. Failure Modes

| Symptom | Likely cause | Action |
|---|---|---|
| CLI exit 2 | Missing/invalid JSON bundle | Fix bundle path and schema |
| Empty `items` | Clean bundle | Expected for healthy snapshots |
| `errors` populated | Quality/architect/readiness sub-evaluator issue | Inspect error strings; fix bundle shape |
| Non-deterministic JSON | Missing `--as-of` / `meta.as_of` | Pass explicit reference timestamp |
