# LR-050 Human Approval — Exakte Freigabeformulierung

- **Control:** `LR-050` (P5 Canary Echtgeld / Live-Kapital)
- **GitHub issue:** [#2534](https://github.com/jannekbuengener/Claire_de_Binare/issues/2534)
- **Document role:** Kanonische Definition der gültigen menschlichen Live-Kapital-Freigabe und der Checkliste davor
- **Last updated:** 2026-06-03
- **Companion:** [`LR-050-DECISION-PACK.md`](./LR-050-DECISION-PACK.md) (Planungskontext, Evidence, TBD-Parameter)
- **Verdict authority (unchanged):** [`LR-AUDIT-STATUS-2026-03-05.md`](./LR-AUDIT-STATUS-2026-03-05.md)

## Safety boundaries (read first)

| Rule | Status |
|------|--------|
| Global `LR-050` verdict | **NO-GO** until a separate, exact human live approval per this document |
| This document authorizes live trading | **No** — kein Live-Go |
| This document authorizes real-money exposure | **No** — kein Echtgeld-Go |
| Merge of PR that adds this document | **Documentation only** — ersetzt **niemals** Human Approval |
| Automatic activation / auto-live | **Forbidden** — No auto-live |
| Board stage `trade-capable` | **Not** live-capital authorization (orthogonal to LR) |
| P5 prestart Human Gate (2026-04-04) | P5 shadow/prestart only — **not** live-capital canary |

Prestart anchor (does **not** grant live-capital GO): [`reports/p5_canary/2026-04-04/decision_record.yaml`](../../reports/p5_canary/2026-04-04/decision_record.yaml).

---

## 1. Rolle und Scope

Dieses Dokument ist die **Single Source of Truth** für:

- wer eine Live-Kapital-Freigabe für `LR-050` erteilen darf,
- die **exakte** wörtliche GO-Formulierung,
- Pflichtparameter in der Freigabe,
- was freigegeben wird und was ausdrücklich nicht,
- welche Aussagen **keine** Freigabe sind,
- Widerruf und Halt.

Es ersetzt keine Kind-Issue-Deliverables ([#2527](https://github.com/jannekbuengener/Claire_de_Binare/issues/2527)–[#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533)). Konkrete Venue-, Limit- und Runbook-Werte bleiben **TBD**, bis die jeweiligen Issues repo-backed liefern.

---

## 2. Wer darf freigeben

| Rule | Detail |
|------|--------|
| **Accountable operator** | Nur **`jannekbuengener`** (konsistent mit [`GO_NO_GO.md`](./GO_NO_GO.md) Owner-Spalte und Decision Pack §8) |
| **Agenten / Session Lead / KI** | Dürfen **keine** Live-Kapital-Freigabe erteilen; Plan-GO, Agent-GO und implizite Zustimmung zählen **nicht** |
| **Delegation** | Nur via expliziten schriftlichen Handoff durch `jannekbuengener` mit benannter Person, Datum (UTC) und Scope; ohne Handoff: **verboten** |
| **Issue-/PR-Merge** | Schließt **kein** Live-Kapital-GO — auch nicht das Merge von [#2534](https://github.com/jannekbuengener/Claire_de_Binare/issues/2534) |

---

## 3. Voraussetzungen vor Freigabe (Checkliste)

Alle Punkte müssen **vor** Ausgabe der GO-Formulierung erfüllt sein. Ein fehlender Punkt = **keine** gültige Freigabe.

| # | Gate | Status (erwartet vor GO) | Owner issue |
|---|------|--------------------------|-------------|
| 1 | Venue-/Broker-/Exchange-Pfad repo-backed dokumentiert | CLOSED + SSOT | [#2527](https://github.com/jannekbuengener/Claire_de_Binare/issues/2527) |
| 2 | Harte Kapital-, Order- und Verlustlimits dokumentiert und prüfbar | CLOSED + SSOT | [#2528](https://github.com/jannekbuengener/Claire_de_Binare/issues/2528) |
| 3 | Kill-Switch- und Stop-Mechanismen verifiziert (Runbook) | CLOSED + SSOT | [#2529](https://github.com/jannekbuengener/Claire_de_Binare/issues/2529) |
| 4 | Secret-Handling ohne Key-Exposure dokumentiert | CLOSED + SSOT | [#2530](https://github.com/jannekbuengener/Claire_de_Binare/issues/2530) — [`LR-050-SECRETS-READINESS.md`](./LR-050-SECRETS-READINESS.md) |
| 5 | Live-Canary-Monitoring und Alert-Gates dokumentiert | CLOSED + SSOT | [`LR-050-OBSERVABILITY-GATES.md`](./LR-050-OBSERVABILITY-GATES.md) ([#2531](https://github.com/jannekbuengener/Claire_de_Binare/issues/2531)) |
| 6 | Erster Echtgeld-Canary-**Plan** (nicht Aktivierung) | CLOSED + SSOT | [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) |
| 7 | Live-Pfad-Dry-Run ohne Order-Placement belegt | CLOSED + SSOT | [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) |
| 8 | Exakte Freigabeformulierung (dieses Dokument) | Repo-backed auf `main` | [#2534](https://github.com/jannekbuengener/Claire_de_Binare/issues/2534) |
| 9 | Operator hat Decision Pack + LR-AUDIT-STATUS + Kind-SSOTs gelesen | Self-attest in GO-Block | — |
| 10 | Globaler LR-Zustand `ready-for-human-live-approval` (optional) | Nur nach [#2535](https://github.com/jannekbuengener/Claire_de_Binare/issues/2535) reconcile | [#2535](https://github.com/jannekbuengener/Claire_de_Binare/issues/2535) |

Matrix-Detail: Decision Pack [§10](./LR-050-DECISION-PACK.md#10-kind-issue-gate-matrix).

---

## 4. Exakte gültige GO-Formulierung

Eine Freigabe ist **nur** gültig, wenn **alle** Bedingungen erfüllt sind:

1. **Erste Zeile (Pflicht-Präfix, wörtlich, Großbuchstaben):**

   ```text
   LR-050 LIVE-CAPITAL HUMAN APPROVAL GRANTED
   ```

2. **Operator-Zeile:** `Operator: jannekbuengener` (oder explizit delegierte Person per Handoff)

3. **Vollständiger Parameterblock** gemäß §5 — **kein** `<TBD>` oder leeres Pflichtfeld

4. **Bestätigungsblock** (wörtlich enthalten):

   ```text
   I confirm:
   - This approval is not inferred from any Issue/PR merge, CI result, or agent action.
   - Auto-live remains forbidden.
   - Child gates #2527–#2533 are CLOSED with repo-backed deliverables reviewed.
   - I have reviewed LR-050-DECISION-PACK.md and LR-050-HUMAN-APPROVAL.md.
   ```

5. **Audit-Kanal (bindend, Priorität):**
   - **Primär:** GitHub-Kommentar auf [#2535](https://github.com/jannekbuengener/Claire_de_Binare/issues/2535) mit vollständigem GO-Text
   - **Sekundär:** Session-Log unter `knowledge/logs/sessions/` mit UTC-Zeitstempel und Verweis auf #2535-Kommentar

6. **UTC-Zeitstempel** der Freigabe im Block: `Approval UTC: <ISO-8601-Z>`

**Mehrdeutigkeit:** Abweichungen vom Präfix, fehlende Pflichtfelder oder paraphrasierte „Zustimmung“ machen die Freigabe **ungültig**.

---

## 5. Pflichtparameter in der Freigabe

Jeder Parameter muss einen **konkreten Wert** aus dem repo-backed SSOT des jeweiligen Kind-Issues tragen. Bis diese Issues liefern, gilt: **kein GO möglich** (Werte bleiben TBD).

| Parameter | In GO-Block (Feldname) | SSOT / Issue | Value (until child issues close) |
|-----------|------------------------|--------------|----------------------------------|
| **Venue** | `Venue:` | [#2527](https://github.com/jannekbuengener/Claire_de_Binare/issues/2527) | TBD |
| **Symbole** | `Symbols:` | [#2528](https://github.com/jannekbuengener/Claire_de_Binare/issues/2528), [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) | TBD |
| **Max-Notional (pro Order)** | `Max notional per order:` | [LR-050-RISK-LIMITS.md](./LR-050-RISK-LIMITS.md) ([#2528](https://github.com/jannekbuengener/Claire_de_Binare/issues/2528)) | TBD (`TBD_BLOCKER_BEFORE_LIVE`) |
| **Max-Notional (Session gesamt)** | `Max notional session total:` | [LR-050-RISK-LIMITS.md](./LR-050-RISK-LIMITS.md) ([#2528](https://github.com/jannekbuengener/Claire_de_Binare/issues/2528)) | TBD (`TBD_BLOCKER_BEFORE_LIVE`) |
| **Max Daily Loss** | `Max daily loss:` | [LR-050-RISK-LIMITS.md](./LR-050-RISK-LIMITS.md) ([#2528](https://github.com/jannekbuengener/Claire_de_Binare/issues/2528)) | TBD (`TBD_BLOCKER_BEFORE_LIVE`) |
| **Laufzeit** | `Duration (UTC window):` | [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) | TBD |
| **Stop-/Kill-Regeln** | `Stop/kill rules:` | [`LR-050-KILL-SWITCH-RUNBOOK.md`](./LR-050-KILL-SWITCH-RUNBOOK.md) ([#2529](https://github.com/jannekbuengener/Claire_de_Binare/issues/2529)) + [`KILL_SWITCH_OPERATOR_CHECKLIST.md`](../operations/KILL_SWITCH_OPERATOR_CHECKLIST.md) | TBD (concrete canary stop criteria from #2532; SSOT structure in runbook) |
| **Startzeitpunkt** | `Start time (UTC):` | Operator + [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) | TBD |
| **Widerruf / Halt** | `Revocation/halt:` | Dieses Dokument §9 | Siehe §9 — Operator kann jederzeit REVOKED ausgeben |

Spiegel (nicht freigebend): Decision Pack [§5](./LR-050-DECISION-PACK.md#5-canary-parameter-tbd--nicht-freigebend).

---

## 6. Was freigegeben wird

Bei **gültiger** GO-Formulierung gemäß §4–§5 ist **ausschließlich** freigegeben:

- **Genau ein** kontrollierter P5 **Live-Kapital-/Crypto-Canary** unter `LR-050`
- Nur innerhalb der im GO-Block genannten Parameter (Venue, Symbole, Notional-, Verlust- und Zeitgrenzen)
- Nur nach **manueller** technischer Aktivierung durch den Operator — **kein** Auto-Live, kein Cron, kein Workflow-Trigger ohne erneute exakte Freigabe
- Nur für die deklarierte Laufzeit; Ende der Laufzeit oder REVOKED beendet die Freigabe

---

## 7. Was ausdrücklich nicht freigegeben wird

| Nicht freigegeben | Detail |
|-------------------|--------|
| Unbegrenztes Live-Kapital / Produktions-Live | Nur explizit begrenzter Canary |
| Symbole oder Venues außerhalb des GO-Blocks | Keine implizite Erweiterung |
| Strategie- oder LR-Gesamt-Freigabe | Nur dieser Canary-Scope |
| Auto-Live / automatische Aktivierung | Verboten |
| Board-Stage `trade-capable` | Orthogonal — kein LR-GO |
| P5-Prestart-GO (2026-04-04) | Shadow/prestart only |
| `MOCK_TRADING="false"` oder Live-Execution ohne diesen GO-Block | Fail-closed |
| Withdrawal-fähige API-Keys | Verboten per [#2530](https://github.com/jannekbuengener/Claire_de_Binare/issues/2530) Scope |

---

## 8. Aussagen, die keine Freigabe sind

Die folgenden (und semantisch gleichwertigen) Aussagen zählen **nicht** als Live-Kapital-Freigabe:

- „LGTM“, „looks good“, „approved“, „ship it“, „go ahead“ (ohne Pflicht-Präfix)
- „merge when green“, „CI is green“, Issue- oder PR-Close, Label-Änderung
- Agent-/Session-Plan-GO, „implement the plan“, Cursor/Codex/OpenCode-Freigaben
- „ready for prod“, „ready for live“, „enable live trading“ (ohne Pflicht-Präfix)
- Implizite Zustimmung, Emoji-only-Zustimmung, vague „we can try live“
- `decision_record.yaml` `status: GO` (P5 prestart only)
- Board-Stage `trade-capable` oder Control-Board-Freigaben
- Schließung von [#2534](https://github.com/jannekbuengener/Claire_de_Binare/issues/2534) oder Merge des Approval-Dokument-PRs
- `ready-for-human-live-approval` ohne nachfolgenden exakten GO-Block per §4

---

## 9. Widerruf und Halt

### 9.1 Widerruf (Pflicht-Präfix)

```text
LR-050 LIVE-CAPITAL HUMAN APPROVAL REVOKED
```

Zusätzlich erforderlich: `Operator:`, `Revocation UTC: <ISO-8601-Z>`, `Reason:` (kurz, sachlich).

**Wirkung:** Sofortiges Ende der Live-Kapital-Autorisierung; keine neuen Live-Orders; Halt gemäß [`LR-050-KILL-SWITCH-RUNBOOK.md`](./LR-050-KILL-SWITCH-RUNBOOK.md) ([#2529](https://github.com/jannekbuengener/Claire_de_Binare/issues/2529)) und [`KILL_SWITCH_OPERATOR_CHECKLIST.md`](../operations/KILL_SWITCH_OPERATOR_CHECKLIST.md).

### 9.2 Operativer Halt (ohne formales REVOKED)

Technischer Halt (Kill-Switch, Trading disable, Allocation 0) ist **jederzeit** erlaubt und **empfohlen** bei Anomalien — ersetzt aber nicht die dokumentierte REVOKED-Zeile für Audit-Zwecke.

### 9.3 Nach Widerruf

Globaler LR-Verdikt bleibt oder kehrt zurück zu **NO-GO** bis [#2535](https://github.com/jannekbuengener/Claire_de_Binare/issues/2535) reconcile.

---

## 10. Issue- und PR-Grenze

| Aktion | Ersetzt Human Approval? |
|--------|-------------------------|
| Merge PR für dieses Dokument (#2534) | **Nein** |
| Close [#2526](https://github.com/jannekbuengener/Claire_de_Binare/issues/2526) / Decision Pack | **Nein** |
| Close [#2527](https://github.com/jannekbuengener/Claire_de_Binare/issues/2527)–[#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) | **Nein** (nur Voraussetzung) |
| CI green / Required checks | **Nein** |
| Exakte GO-Formulierung §4 auf #2535 (oder sekundär Session-Log) | **Ja** (einziger Live-Kapital-GO-Pfad) |

---

## 11. Auto-Live

- **Verboten:** Schedules, Hooks, Compose-Defaults, Feature-Flags oder Agenten dürfen Live-Kapital **nicht** ohne den exakten GO-Block §4 aktivieren.
- **Fail-closed:** Bei Unklarheit gilt **NO-GO**.

---

## 12. LR-Verdikt

| Zustand | Bedingung |
|---------|-----------|
| **NO-GO** (aktiv) | Standard bis ein gültiger GO-Block §4 existiert **und** Operator Live-Aktivierung manuell ausführt |
| **ready-for-human-live-approval** | Nur nach [#2535](https://github.com/jannekbuengener/Claire_de_Binare/issues/2535) — bedeutet „bereit zur Prüfung“, **nicht** Live-Freigabe |
| **GO** (live-capital) | Nur mit gültigem §4-Text; nie allein durch Issue/PR |

SSOT: [`LR-AUDIT-STATUS-2026-03-05.md`](./LR-AUDIT-STATUS-2026-03-05.md). Roadmap: [`ROADMAP.yaml`](./ROADMAP.yaml) — `requires: explicit_human_approval`.

---

## 13. Copy-Paste-Vorlagen

### 13.1 GO-Vorlage (nicht ausfüllen bis #2527–#2533 SSOTs liegen)

```text
LR-050 LIVE-CAPITAL HUMAN APPROVAL GRANTED

Operator: jannekbuengener
Approval UTC: <ISO-8601-Z>

Venue: <TBD — from #2527 SSOT>
Symbols: <TBD — from #2528/#2532 SSOT>
Max notional per order: <TBD — from #2528 SSOT>
Max notional session total: <TBD — from #2528 SSOT>
Max daily loss: <TBD — from #2528 SSOT>
Duration (UTC window): <TBD — from #2532 SSOT>
Stop/kill rules: <TBD — from #2529 SSOT; ref KILL_SWITCH_OPERATOR_CHECKLIST>
Start time (UTC): <TBD>
Revocation/halt: I may revoke at any time by issuing: LR-050 LIVE-CAPITAL HUMAN APPROVAL REVOKED

I confirm:
- This approval is not inferred from any Issue/PR merge, CI result, or agent action.
- Auto-live remains forbidden.
- Child gates #2527–#2533 are CLOSED with repo-backed deliverables reviewed.
- I have reviewed LR-050-DECISION-PACK.md and LR-050-HUMAN-APPROVAL.md.
```

### 13.2 REVOKED-Vorlage

```text
LR-050 LIVE-CAPITAL HUMAN APPROVAL REVOKED

Operator: jannekbuengener
Revocation UTC: <ISO-8601-Z>
Reason: <short factual reason>
```

---

## Related documents

- [`LR-050-DECISION-PACK.md`](./LR-050-DECISION-PACK.md) — Planungskontext und Gate-Matrix
- [`LR-050-KILL-SWITCH-RUNBOOK.md`](./LR-050-KILL-SWITCH-RUNBOOK.md) — Stop/Halt SSOT ([#2529](https://github.com/jannekbuengener/Claire_de_Binare/issues/2529))
- [`README.md`](./README.md) — Live-readiness index
- [`docs/operations/P5_PRESTART_PACK.md`](../operations/P5_PRESTART_PACK.md) — Prestart (nicht Live-Kapital)
- [`docs/runbooks/CONTROL_REGISTER.md`](../runbooks/CONTROL_REGISTER.md) — Board stage vs LR
