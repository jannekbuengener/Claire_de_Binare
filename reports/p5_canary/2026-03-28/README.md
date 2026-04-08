# P5 Prestart Pack — 2026-03-28

**Status: NO-GO / IN PREPARATION**

Dieses Verzeichnis ist das vorbereitete Skeleton für den nächsten vollständigen P5-Prestart-Pack.
Es enthält Templates und Placeholder-Anker. **Kein Artefakt hier ist operativ abgeschlossen.**

---

## Zustand dieses Artefakt-Satzes

| Datei | Zustand | Aktion erforderlich |
|---|---|---|
| `prestart_evidence_lock.yaml` | TEMPLATE | Operator: BLUE-Stack starten, curl-Captures durchführen, alle `<OPERATOR_FILL>` ersetzen |
| `decision_record.yaml` | TEMPLATE | Operator: nach LR-040-Verdict + Human Gate ausfüllen |
| `manifest.json` | TEMPLATE | Operator: nach allen Captures + checksums berechnen |
| `lr040/lr040_soak_gate_eval.json` | PLACEHOLDER | Nach Soak-Ende: Evaluator laufen lassen, Output diese Datei ersetzen |
| `endpoints/execution_status.json` | **FEHLT** | Operator: `curl -s http://127.0.0.1:8003/status > endpoints/execution_status.json` |
| `endpoints/risk_status.json` | **FEHLT** | Operator: `curl -s http://127.0.0.1:8002/status > endpoints/risk_status.json` |
| `endpoints/kill_switch_status.json` | **FEHLT** | Operator: `curl -s http://127.0.0.1:8002/kill-switch > endpoints/kill_switch_status.json` |

---

## Operator-Checkliste (in dieser Reihenfolge)

### Schritt 1 — LR-040 Gate-Evaluator (ab 2026-03-28 12:12 UTC)

```bash
# LR-040-Evaluator mit dem Soak-Artefaktverzeichnis aufrufen
python infrastructure/scripts/lr040_soak_gate_eval.py artifacts/soak_test_20260325_121250
# Verdict prüfen: PASS, FAIL oder INCONCLUSIVE
# Evaluator schreibt Output nach:
#   artifacts/soak_test_20260325_121250/lr040_soak_gate_eval.json
# Dieses JSON in den Prestart-Pack kopieren:
cp artifacts/soak_test_20260325_121250/lr040_soak_gate_eval.json \
   reports/p5_canary/2026-03-28/lr040/lr040_soak_gate_eval.json
```

Soak-Run-Artefaktpfad: `artifacts/soak_test_20260325_121250`

### Schritt 2 — BLUE-Stack sicherstellen

```bash
docker compose -f infrastructure/compose/compose.blue.yml ps
# Alle 10 BLUE-Services müssen laufen (Ports 8002, 8003 erreichbar)
```

### Schritt 3 — Endpoint-Captures (live)

```bash
mkdir -p reports/p5_canary/2026-03-28/endpoints

curl -s http://127.0.0.1:8002/kill-switch > reports/p5_canary/2026-03-28/endpoints/kill_switch_status.json
curl -s http://127.0.0.1:8003/status      > reports/p5_canary/2026-03-28/endpoints/execution_status.json
curl -s http://127.0.0.1:8002/status      > reports/p5_canary/2026-03-28/endpoints/risk_status.json
```

**Pflicht-Checks auf den Captures:**
- `execution_status.json` → `.mode` muss `"mock"` sein
- `risk_status.json` → `.risk_state.circuit_breaker` muss `false` sein
- `kill_switch_status.json` → `.active` muss `false` sein

### Schritt 4 — prestart_evidence_lock.yaml ausfüllen

```bash
git rev-parse HEAD          # → commit_sha
git status --porcelain      # muss leer sein (worktree_status: clean)
date -u +%Y-%m-%dT%H:%M:%SZ  # → evidence_lock_utc und captured_utc
```

Alle `<OPERATOR_FILL>`-Felder in `prestart_evidence_lock.yaml` ersetzen.
`gate_summary.all_gates_pass: true` nur setzen wenn alle drei Gates `true` sind.

### Schritt 5 — decision_record.yaml ausfüllen

```bash
date -u +%Y-%m-%dT%H:%M:%SZ  # → decision_utc
git rev-parse HEAD             # → source_commit_sha (= gleicher Wert wie in evidence_lock)
```

- `lr040_verdict`: aus Schritt 1 übernehmen
- `status: GO` nur setzen wenn: LR-040 PASS + all_gates_pass: true + Human Gate erteilt
- Sonst: `status: NO-GO` mit Begründung

### Schritt 6 — manifest.json finalisieren

Checksums aller Dateien berechnen (Bash):
```bash
for f in prestart_evidence_lock.yaml decision_record.yaml \
          endpoints/execution_status.json endpoints/risk_status.json \
          endpoints/kill_switch_status.json lr040/lr040_soak_gate_eval.json; do
  echo "$f: $(sha256sum reports/p5_canary/2026-03-28/$f | awk '{print $1}')"
done
```

Werte in `manifest.json` → `checksums.files` eintragen.
`source_integrity.all_required_paths_present: true` setzen.

### Schritt 7 — Commit

```bash
git add reports/p5_canary/2026-03-28/
git status  # 8 Dateien erwartet: 7 P5-Core-Dateien + README.md
git commit -m "docs(p5): prestart evidence pack 2026-03-28 — [GO|NO-GO]"
```

### Schritt 8 — Lean-Shadow-Evidence-Run triggern (nur bei GO-Entscheidung)

```bash
gh workflow run shadow-soak-evidence.yml --ref main -f mode=lean
gh run watch $(gh run list --workflow=shadow-soak-evidence.yml --limit=1 \
  --json databaseId --jq '.[0].databaseId') --exit-status
```

---

## Kein GO ohne alle sieben Dateien committed

Der P5-Lean-Run bleibt blockiert bis:
1. `lr040/lr040_soak_gate_eval.json` → verdict: PASS
2. `prestart_evidence_lock.yaml` → runtime-captured, all_gates_pass: true
3. `decision_record.yaml` → status: GO, Human Gate erteilt
4. `manifest.json` → checksums vollständig
5. `endpoints/*.json` (3 Dateien) → live gecaptured
