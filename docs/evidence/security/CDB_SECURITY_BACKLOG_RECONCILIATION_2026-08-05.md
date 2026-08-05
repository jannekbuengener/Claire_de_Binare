# Security Backlog Reconciliation — 2026-08-05

**Anchor:** [#2513](https://github.com/jannekbuengener/Claire_de_Binare/issues/2513)  
**Machine inventory:** [`CDB_SECURITY_ALERT_INVENTORY_2026-08-05.json`](CDB_SECURITY_ALERT_INVENTORY_2026-08-05.json)  
**Machine reconciliation:** [`CDB_SECURITY_BACKLOG_RECONCILIATION_2026-08-05.json`](CDB_SECURITY_BACKLOG_RECONCILIATION_2026-08-05.json)  
**Base at fetch:** `origin/main` @ `10ac6f95c2e4d5f9b3ce2530d2c5ad36aff3794e`  
**Routing:** `CREATE_DEDICATED_PR` → `dedicated/runtime-risk-issue-2513`  
**LR:** NO-GO · Board stage `trade-capable` (orthogonal)  
**Policy:** no alert dismissal · no `.trivyignore` growth · no scanner weakening

---

## Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
tools_or_queries:
  - MCP cdb_context_briefing (task cdb-briefing-2513-security-backlog-recon-2026-08-05)
  - gh api repos/.../code-scanning/alerts?state=open (11 pages, per_page=100)
repo_crosscheck:
  - docs/evidence/security/* prior waves
  - CURRENT_STATUS.md / CONTROL_REGISTER.md / LR-AUDIT-STATUS
impact_on_plan:
  - Full live inventory required; no DB-backed claims
limitations:
  - Context trust none; no enrichment records
context_brain_attempted: true
context_brain_used: false
context_available: false
repo_fallback_used: true
repo_fallback_reason: insufficient_evidence
context_tool_status: available
context_trust_level: none
records_found: none
```

---

## Start inventory (GitHub live, 2026-08-05)

| Metric | Count |
|--------|------:|
| Open code-scanning alerts | **1010** |
| Unique alert numbers | **1010** |
| Trivy | 943 |
| CodeQL | 63 |
| Gitleaks | 4 |
| Critical | 32 |
| High | 196 |
| Medium | 399 |
| Low | 89 |
| none (no security_severity_level) | 294 |
| Root-cause groups | 157 |
| Open `type:security` issues | 18 |

Query evidence: `Link: ...&page=1010>; rel="last"` on
`GET /repos/jannekbuengener/Claire_de_Binare/code-scanning/alerts?state=open&per_page=1`.

---

## Disposition summary (alert-level)

| Disposition | Alerts |
|-------------|-------:|
| `UPSTREAM_BLOCKED` | 897 (+ postgres c-ares after live digest recheck) |
| `FIX_READY` | ~93 initial classifier; pip HIGH subset actively remediated |
| `DUPLICATE_CANONICAL_TRACKER` | 16 (Grafana zipkin plugin wave) |
| `NEEDS_EVIDENCE` / refined FP | 4 Gitleaks + stale CodeQL HIGH |

Allowed dispositions used in this campaign match the Plan-GO enum. **No dismissals.**

---

## Priority 0 — Gitleaks (4)

| Alert | Path | Tip status | Disposition |
|------:|------|------------|-------------|
| 5692–5694 | `reports/shadow_mode/*` | **deleted** from tree (#4099) | `FALSE_POSITIVE_WITH_PROOF` for tip exposure; historical residual remains open (no history rewrite; no dismissal) |
| 5500 | `knowledge/deep-issues-lab/cdb_execution.md` | Tip already uses `REDACTED_*` placeholders | `FALSE_POSITIVE_WITH_PROOF` for tip; alert may lag until scanner re-baseline |

Owner action: if any historical credential was ever real, rotate via the normal owner channel (`SECRET_OWNER_ACTION_REQUIRED` for rotation only — not performed in this session). No secret values were copied into evidence.

---

## Priority 1 — Critical/High with FixedVersion

### Directly fixable (CDB-owned pins)

| Root cause | Fixed | Action |
|------------|-------|--------|
| `aiohttp` 3.14.1 → 3.14.3 | CVE-2026-69244 HIGH | PR `dedicated/security-pip-crypto-aiohttp-2026-08-05` |
| `cryptography` 48.0.1/49.0.0 → 50.0.0 | CVE-2026-69247 HIGH (+ 69248/69249) | same PR |
| `setuptools` 82.0.0 → 83.0.0 | CVE-2026-59890 MEDIUM | PR `dedicated/security-setuptools-83-2026-08-05` |

### Not fixable by CDB despite FixedVersion string

| Root cause | Why blocked | Tracker |
|------------|-------------|---------|
| Debian Trixie OS packages with **empty** FixedVersion (perl-base, gzip, libacl1, util-linux, curl…) | Suite-native unfixed | #2513 / #2932 / #3802 / #3803 / #3936 / #4080 / #4106 / #4114 |
| Grafana bundled zipkin / elasticsearch Go stdlib & x/net | Cannot rebuild Grafana plugin binaries | **#2933** (issues #4350–#4356, #4359) |
| `postgres:18.4-alpine` `c-ares` 1.34.6-r0 FixedVersion 1.34.8-r0 | Live tip digest `9a8afca5…` still ships 1.34.6-r0 (Trivy 0.73.0) | **#2933** |

Already processed (do not re-open as unsolved): PR #4363 @ `ee2a5c81` cleared Grafana binary/elasticsearch path issues #4357/#4358.

---

## Priority 2 — CodeQL

63 open CodeQL alerts. HIGH clear-text storage/logging alerts (#4535/#4612/#4611/#4533) analyze against stale SHA `64e2a774` **before** #3925 hardening on tip. Tip already redacts / sidecars secrets; disposition `FALSE_POSITIVE_WITH_PROOF` / `NEEDS_EVIDENCE` pending fresh CodeQL on tip. Quality rules (unused-import, empty-except, …) are safe cosmetics — optional later batch; not Critical/High security blockers.

---

## Priority 4 — Canonical trackers (no parallel structure)

| Tracker | Role |
|---------|------|
| #2513 | Meta upstream-blocked Trivy residuals |
| #2932 | perl-base cluster |
| #2933 | Grafana / Prometheus / Postgres (+ zipkin wave) |
| #3705 / #3802 / #3803 / #3936 | OS residual clusters |
| #4080 | curl CVE-2026-8286 canonical |
| #4106 / #4114 | perl Critical/High HOLDs |

Per-alert zipkin issues #4350–#4356, #4359 → close as **tracking duplicates of #2933** after this evidence lands (alerts stay open).

---

## Remediations this campaign

1. Pip HIGH pin PR (aiohttp/cryptography).
2. Setuptools MEDIUM pin PR across Dockerfiles.
3. This evidence pack + inventory JSON (100% of start-open alerts).
4. Issue consolidation comments / closes for zipkin duplicates under #2933.
5. Dependabot #4348/#4349 superseded by pip PR (close after merge).

Forbidden actions **not** taken: dismissals, `.trivyignore` growth, scanner disable, admin merge, LR/live changes, history rewrite.

---

## Closure / re-eval dates

| Cluster | Re-eval |
|---------|---------|
| perl-base / #4106 / #4114 | **2026-08-15** or Debian FixedVersion |
| curl / #4080 / #3936 | when Debian publishes fixed curl |
| Grafana zipkin / #2933 | next Grafana upstream image with rebuilt plugins |
| postgres c-ares / #2933 | Alpine/postgres ships `c-ares>=1.34.8-r0` |
| Gitleaks historical | owner rotation decision if credential was real; no tip exposure |
| CodeQL HIGH stale | next CodeQL Python run on `main` tip |

---

## Validation

- Inventory pagination: 11 × ≤100 pages = 1010 alerts.
- Postgres candidate digest Trivy: CVE-2026-33630 **still present** on newest `postgres:18.4-alpine`.
- Pip contract tests added in companion PR.
- No alert dismissed in this campaign.
