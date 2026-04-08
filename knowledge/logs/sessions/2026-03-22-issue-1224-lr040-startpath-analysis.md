# Session Log: 2026-03-22 — Issue #1224 LR-040 Startpfad-Analyse

**Topic:** LR-040 Startpfad, Prestart-Evidence-Lock, Human Gate — operative Vorbereitung
**Branch:** fix/lr031-liveness-threshold-1224 → main (PR #1257 gemergt)
**Kontext:** Fortsetzung von Session 3 (P5 lean run + LR-031 Threshold-Kalibrierung)

---

## 1. Ausgangslage

Lean-Run `23407946292` (nach PR #1257 Merge, Commit `1a700f3`) ist vollständig PASS:
- soak_gate: PASS
- comparison (signals_received=6 >= min=1, orders_blocked=6 >= min=1): PASS
- canonical package: BUILT (fail-closed, jetzt PASS)

PR #1257 (`fix/lr031-liveness-threshold-1224`) gemergt via squash auf main.
`docs/evidence/lr031_baseline_thresholds.json`: signals_received + orders_blocked auf min=1 (liveness floor).

---

## 2. PR #1237 — BLOCKIERT

`gh pr view 1237` Ergebnis:

| Check | Wert |
|---|---|
| mergeStateStatus | DIRTY |
| mergeable | CONFLICTING |
| CI | FAILURE |
| policy-gate | FAILURE (missing allow-core-change label) |

Ursache: PR #1237 wurde am 2026-03-20 erstellt. Seitdem landeten PR #1226 (squash df169f4) und PR #1257 (squash 1a700f3) auf main — beide betreffen Dateien, die PR #1237 ebenfalls modifiziert. Merge-Konflikte entstanden.

**Konsequenz:** PR #1237 kann in dieser Session nicht gemergt werden. Er fügt `check_lr040_runtime_env.sh` und ergänzende Runtime-Prep-Checks hinzu — nützlich, aber nicht zwingend für den LR-040-Start. Die Kern-Werkzeuge (soak_monitor.sh, lr040_soak_gate_eval.py, Runbook) existieren bereits auf main.

---

## 3. LR-040 Startpfad

**Kritischer Befund: LR-040 hat KEINEN GitHub Actions Workflow.**

`shadow-soak-evidence.yml` ist der Shadow-Evidence-Workflow (lean=5min, full=30min) für LR-030/031. Er ist NICHT der 72h-Soak.

Der 72h-Soak ist ein **lokaler/manueller Prozess** auf dem Windows-/WSL2-Rechner.

### Kanonischer Startpfad

1. **Pre-flight (Runbook §Windows Host):**
   - Windows Update: pausieren für Dauer des Soaks
   - Pending-Reboot-Check: `pending_reboot=$(powershell.exe -Command "...")`
   - Bei pending reboot: ERST rebooten, DANN Soak starten
   - BLUE-Stack prüfen: alle Container healthy

2. **Prestart-Evidence-Lock erfassen** (unmittelbar vor Soak-Start, BLUE-Stack muss laufen — siehe §4)

3. **WSL2-Shell öffnen**, in Repo-Root navigieren

4. **Soak starten:**
   ```bash
   bash infrastructure/scripts/soak_monitor.sh > artifacts/soak_test_$(date +%Y%m%d_%H%M%S)/soak_monitor.log 2>&1 &
   ```
   Oder via cron (kanonisch laut Runbook).

5. **Nach 72h — Gate-Evaluator:**
   ```bash
   python infrastructure/scripts/lr040_soak_gate_eval.py artifacts/soak_test_YYYYMMDD_HHMMSS/
   ```

6. **Nach PASS:**
   - Committed Reference Anchor: `reports/p5_canary/<YYYY-MM-DD>/lr040/lr040_soak_gate_eval.json`
   - Ersetzt den Placeholder in `reports/p5_canary/2026-03-20/lr040/lr040_soak_gate_eval.json` (verdict: NOT_RUN)

**Kein `gh workflow run` für LR-040 möglich — lokale WSL2-Ausführung zwingend.**

---

## 4. Prestart-Evidence-Lock

### Aktueller Stand

`reports/p5_canary/2026-03-20/prestart_evidence_lock.yaml`:
- `evidence_lock_utc: NOT_CAPTURED`
- `kill_switch.active: NOT_CAPTURED`
- `execution_status.mode: mock` (normativ eingetragen, **nicht** live erfasst)
- `risk_status.circuit_breaker: NOT_CAPTURED`
- `capture_state: no_runtime_capture`

Das ist ein committed Placeholder — es hat keine echte Laufzeit-Erfassung stattgefunden.

### Capture-Zeitpunkt

**Die echten Runtime-Werte müssen unmittelbar VOR dem LR-040 Soak-Start erfasst werden**, während der BLUE-Stack läuft. Nicht nach LR-040 PASS.

### Capture-Pfad (vollständig, kein Repo-Delta nötig)

Template und Capture-Kommandos: `docs/operations/P5_PRESTART_PACK.md` §3

```bash
# BLUE-Stack muss laufen
curl -s http://127.0.0.1:8002/kill-switch   # kill_switch.active == false required
curl -s http://127.0.0.1:8003/status         # execution_status.mode == mock required
curl -s http://127.0.0.1:8002/status         # risk_state.circuit_breaker == false required
```

Werte in neues Datum-Verzeichnis `reports/p5_canary/<YYYY-MM-DD>/prestart_evidence_lock.yaml` eintragen, committed vor Soak-Start.

**Status: capture-ready. Kein Repo-Delta erforderlich.**

---

## 5. Human Gate / Decision Record

### Aktueller Stand

`reports/p5_canary/2026-03-20/decision_record.yaml`:
- `decision_utc: NOT_CAPTURED`
- `operator: pending_operator_assignment`
- `lr040_pass_run_id: NOT_AVAILABLE`
- `status: NO-GO`

### Gate-Pfad

Template: `docs/operations/P5_PRESTART_PACK.md` §5

Pflichtfelder nach LR-040 PASS:
- `decision_utc`: Zeitpunkt der Entscheidung
- `operator`: Jannek (menschlicher Operator)
- `lr040_pass_run_id`: Artifact-ID des LR-040 PASS-Runs
- `lr040_pass_commit`: Commit-SHA auf dem LR-040 lief
- `status: GO | NO-GO`
- `rationale`: Begründung

`lr040_pass_run_id` und `lr040_pass_commit` können erst nach LR-040 PASS eingetragen werden.

**Status: operativ vorbereitet. Kein Repo-Delta erforderlich.**

---

## 6. Bewertung

| Blocker | Status | Nächster Schritt |
|---|---|---|
| LR-031 Threshold-Kalibrierung | DONE (PR #1257, min=1) | — |
| Shadow lean run PASS | DONE (Run 23407946292) | — |
| PR #1237 (Runtime-Env-Prep) | BLOCKIERT (DIRTY/CONFLICTING, CI FAIL) | Konflikte resolven, label setzen |
| Prestart-Evidence-Lock | NOT_CAPTURED | Vor LR-040 Start erfassen (curl §3, BLUE-Stack laufend) |
| LR-040 72h Soak | NICHT GESTARTET | Manuell in WSL2 starten (Runbook §Windows Host) |
| Human Gate / Decision Record | NOT_CAPTURED | Nach LR-040 PASS: §5 ausfüllen, Jannek-Entscheidung |

**Operative Gesamtverdikt: NO-GO** — LR-040 und Human Gate ausstehend.

---

## 7. Nächste Schritte

1. PR #1237: Konflikte resolven (git rebase/merge origin/main), `allow-core-change` Label setzen, CI-Run abwarten
2. Prestart-Evidence-Lock erfassen: BLUE-Stack starten, curl-Capture aus §3, in `reports/p5_canary/<YYYY-MM-DD>/` committen
3. LR-040 72h Soak starten: WSL2-Shell, Runbook §Windows Host befolgen — unmittelbar nach Prestart-Capture
4. Nach LR-040 PASS: Human Gate (§5) — Jannek entscheidet GO/NO-GO, decision_record.yaml ausfüllen
