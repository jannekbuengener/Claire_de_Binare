# ARVP Readonly Preflight Closeout — #2967

**Decision Date:** 2026-06-08
**Decision:** **CLOSEOUT_READONLY_PREFLIGHT**
**Preflight Status:** **INFRA_AND_RUNNER_VALIDATED**
**Issue Status:** → **CLOSE**

---

## Brain Evidence

| Field | Value |
|-------|-------|
| `brain_source` | `repo-only` |
| `brain_status` | `not-used` |
| `tools_or_queries` | `gh issue view` (2967, 2968, 2969, 3087, 1900), `gh pr list`, `git log`, `rg` |
| `records_or_results` | 5 live GitHub queries; 2 existing evidence docs; 1 runner source file; 0 DB queries |
| `repo_crosscheck` | All evidence GitHub+repo-backed; no DB/MCP/brain claims |
| `impact_on_plan` | Infra PASS proven from #2967 comments; runner validated via #2969 closeout; closeout is docs-only |
| `limitations` | No independent DB verification (not allowed, not needed); evidence is redacted GitHub comments + downstream proof |

---

## Bootloader / Read-Order Evidence

- `AGENTS.md` root pointer resolved ✅
- `agents/AGENTS.md` read (canonical registry, read order, brain evidence gate) ✅
- `knowledge/governance/CDB_CONSTITUTION.md` ✅
- `docs/runbooks/CONTROL_REGISTER.md`: Board stage `trade-capable`, LR `NO-GO` ✅
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`: LR verdict `NO-GO` ✅
- `CURRENT_STATUS.md`: Ledger-only, not live truth ✅
- Git truth: HEAD (`e22122f`) == `origin/main`, clean worktree, 0 open PRs ✅

---

## Live-Lage (GitHub Live Truth as of 2026-06-08)

| Issue | State | Relevance |
|-------|-------|-----------|
| #2967 | **OPEN** | This closeout — readonly preflight status |
| #2969 | **CLOSED** | Runner extraction validated with `cdb_readonly` (unblocked 2026-06-06) |
| #2968 | **OPEN** | Paper runtime producer for new comparison-grade chains |
| #3087 | **OPEN** | Hard blocker: longer windows with `regime_segments` |
| #1900 | **OPEN** | ARVP north-star anchor, Phase A BLOCKED (§5.2.4) |
| #2961 | **CLOSED** | Calibration batch completed (2-window bank) |
| PR #3028 | **MERGED** (af01c76c) | Delivered `paper_reference_window.v1` artifact, runner validated |

---

## #2967 Acceptance Criteria — Full Reassessment

### Original Criteria (from #2967 body)

| # | Criterion | Verdict | Evidence |
|---|-----------|---------|----------|
| 1 | `cdb_readonly` role exists | **PASS** | [Comment #4630984062](#2967): DB role surface PASS — `rolcanlogin=true`, `rolsuper/createdb/createrole=false` |
| 2 | CONNECT on `claire_de_binare` | **PASS** | Ibid: `CONNECT=true` |
| 3 | USAGE on `public` schema | **PASS** | Ibid: `USAGE=true` |
| 4 | SELECT on `public.correlation_ledger` | **PASS** | Ibid: `SELECT=true` |
| 5 | No INSERT/UPDATE/DELETE | **PASS** | Ibid: `INSERT=false; UPDATE=false; DELETE=false` |
| 6 | `POSTGRES_READONLY_PASSWORD_DSN` set (redacted) | **PASS** | Ibid: `DSN status: set` (redacted — no value in outputs) |
| 7 | Runner identity self-check | **PASS** | Ibid: `Readonly session identity: PASS (current_user=cdb_readonly; session_user=cdb_readonly)` |
| 8 | Runner extracts known pilot window | **VALIDATED** | For #2967 at time of check (2026-06-05): FAIL due to `chain-integrity: no SIGNAL anchors`. Data gap, not infra gap. **Subsequently validated** via #2969 closeout: runner successfully exported `paper_reference_window.v1` with `DB identity confirmed: cdb_readonly, SELECT-only` (PR #3028, af01c76c). |
| 9 | No secret values in outputs | **PASS** | All comments redacted; no DSN, password, or token in #2967 thread, this doc, or downstream artifacts |

### Result

- **Criteria 1–7, 9**: **PASS** — Infra-Setup vollständig und verifiziert
- **Criterion 8**: **VALIDATED** — Ursprünglich HOLD wegen fehlender SIGNAL-Anker (Data-Gap). Durch #2969/#3028 nachträglich validiert: `paper_reference_window_runner.py` extrahiert erfolgreich mit `cdb_readonly`-Identität.

---

## Infra vs Data — Trennungsanalyse

### Runner-Code-Struktur

`services/validation/paper_reference_window_runner.py` trennt zwei Phasen sauber im Quellcode:

| Phase | Funktion | Zeilen | Prüft |
|-------|----------|--------|-------|
| Identity Self-Check | `_verify_readonly_identity()` | 110–131 | `current_user`/`session_user` = `cdb_readonly` |
| Privilege Check | `_verify_readonly_privileges()` | 134–153 | `SELECT=true`, `INSERT/UPDATE/DELETE=false` |
| Extraction | `export_paper_reference_window()` | 269–276 | Chain-Integrität, SIGNAL-Anker, Kontrakt-Validierung |

### Ursprünglicher Failure in #2967

Der Exit-Code-2 kam vom `PaperReferenceExportError`-Pfad (Zeile 274–276), **nicht** von `_verify_readonly_identity` oder `_verify_readonly_privileges`. Die Infra-Selbsttests (Identity + Privileges) waren alle PASS.

Fehlerursache: `chain-integrity failed: window contains no SIGNAL anchors` — ein **Data-Precondition-Problem**, kein Infra-Problem. Der `correlation_ledger` enthielt zum Zeitpunkt der Prüfung keine comparison-grade Chain mit SIGNAL-Ankern.

### Nachträgliche Validierung via #2969

#2969 wurde 2026-06-06 geschlossen. PR #3028 (Merge-SHA `af01c76c`) brachte ein `paper_reference_window.v1`-Artefakt ins Repo, das der Runner erfolgreich mit `cdb_readonly`-Identität extrahiert hatte (Beleg: #2969-Kommentar 2026-06-06T01:01:38Z: "DB identity confirmed: cdb_readonly, SELECT-only").

Damit ist Kriterium 8 **nachträglich validiert** — nicht nur die Infrastruktur, sondern auch der Runner-Extraktionspfad mit `cdb_readonly`-Identität funktioniert.

---

## Entscheidung: INFRA_AND_RUNNER_VALIDATED → CLOSE #2967

### Begründung

1. **Infra-Setup (Kriterien 1–7): PASS** — `cdb_readonly` role existiert, DSN gesetzt (redacted), Privilegien korrekt (SELECT-only, keine Schreibrechte), Identity-Selbsttest bestanden.
2. **Runner-Extraktion (Kriterium 8): VALIDATED** — Durch #2969/#3028 nachträglich belegt. Der Runner extrahiert erfolgreich mit `cdb_readonly`-Identität.
3. **Secret-Safety (Kriterium 9): PASS** — Keine Secret-Werte in Issues, Kommentaren, PRs oder Repo-Dateien.
4. **Keine offenen Infra-Reste** — Alle Infra-Kriterien sind erfüllt. Der verbleibende Data-Blocker (längere Windows mit `regime_segments`) gehört zu #3087, nicht zu #2967.

### #2967 kann geschlossen werden.

Die ursprüngliche Zielsetzung — `cdb_readonly` role, DSN, und validierte read-only Extraktion — ist vollständig erfüllt.

---

## Downstream Mapping

### Bereits gelöst

| Issue | Titel | Status |
|-------|-------|--------|
| #2969 | Extract comparison-grade paper_reference_window.v1 entries | **CLOSED** (DONE_RECONCILED_CLOSED) |
| #3028 | Paper reference window artifact commit | **MERGED** (af01c76c) |

### Offene Blocker (nicht in #2967 Scope)

| Issue | Titel | Warum nicht #2967-Scope |
|-------|-------|-------------------------|
| #3087 | Longer windows with non-empty `regime_segments` | Data-Quality-Gate für Phase A Product-Complete, kein Infra-Setup |
| #2968 | Paper runtime — produce new paper-prefixed windows | Producer/Data-Generierung, kein readonly Infra-Setup |

### Beziehung zu Parent-Issues

| Parent | Relevanz |
|--------|----------|
| #1900 | ARVP north-star anchor. #2967-Closeout löst Phase A Infra-Preflight. Product-Complete weiterhin BLOCKED durch #3087. |
| #2961 | ARVP calibration batch. #2967 war A1-Enabler. Mit #2969 + #3028 ist Extraktion validiert. |
| #1784 | 14-day paper phase. Historischer Kontext, nicht durch #2967 betroffen. |

---

## Safety Boundaries

| Rule | Status |
|------|--------|
| LR remains NO-GO | Enforced |
| No Live-Go / Echtgeld-Go | Enforced |
| No DB mutation in this slice | Enforced (no DB access) |
| No runtime start/stop | Enforced |
| No Docker orchestration | Enforced |
| No secrets in outputs | Enforced (verified via rg scan) |
| Board stage `trade-capable` does not authorize live capital | Enforced |
| Infra-PASS claims based on redacted GitHub comments | Explicit — no independent DB verification performed |
| #2967 closeout does not imply #1900 or Phase A product-complete | Enforced |

---

## Validation (this slice)

```bash
# Secret-scan: null findings
rg -n "postgres://|postgresql://|password=|SECRET|TOKEN|API_KEY" docs/evidence/arvp_readonly_preflight_2967_closeout.md

# Live-Go check: only NO-GO / Safety references found
rg -n "Live-Go|Echtgeld|LIVE_TRADING_CONFIRMED|MEXC_TESTNET=false|MOCK_TRADING=false|DRY_RUN=false" docs/evidence/arvp_readonly_preflight_2967_closeout.md
```

- ✅ Secret-scan: 0 echte Secrets gefunden
- ✅ Live-Go: alle Treffer sind NO-GO / Safety-Beschreibungen
- ✅ Diff docs-only (1 neue Datei)
- ✅ Keine Code-, Runtime-, DB- oder Workflow-Änderungen

---

## Restunsicherheiten

1. **Infra-PASS basiert auf redacted GitHub-Kommentaren** (#4630984062, #4631048177). Keine unabhängige DB-Verifikation wurde in diesem Slice durchgeführt (und wäre nicht erlaubt). Die Kommentare sind vom Owner (`jannekbuengener`) und belegen explizit alle Privilege-Checks — sie gelten als verlässliche Evidence.
2. **Keine Secrets gesehen.** DSN, Passwort und Rollen-Details sind redacted. Die Tatsache, dass die DSN gesetzt ist, ist belegt; der Wert wurde nie gesehen oder ausgegeben.
3. **#2969-Closeout belegt Runner-Validierung** mit `cdb_readonly`-Identität. Das ersetzt nicht den direkten #2967 Self-Check gegen den Pilot-Anker, aber es bestätigt, dass der Runner-Extraktionspfad mit `cdb_readonly` vollständig funktioniert.

---

## Quellen

- `services/validation/paper_reference_window_runner.py` — Runner source (294 lines, identity/privilege/export separation)
- `docs/evidence/arvp_window_bank_2961_extraction_2026-06-04.md` — Original extraction audit
- `docs/evidence/arvp_2961_paper_window_runtime_preflight_2026-06-04.md` — Runtime preflight
- `docs/evidence/arvp_product_complete_review_2974.md` — Phase A product-complete gate review
- `docs/roadmaps/ARVP_TO_LIVE_GO_ROADMAP_2026-06.md` — Phase A roadmap
- GitHub: #2967 (comments #4630984062, #4631048177), #2969 (closeout evidence), #3028 (merged PR)
