<!--
Canonical Skill Source: docs/skills/cdb-control-intake/SKILL.md
Surface: claude
Sync Status: mirrored-from-canon
Last Verified: 2026-08-11
Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.
-->
---
name: cdb-control-intake
description: >
  Rebuilds a fail-closed CDB control snapshot from canonical repo and GitHub
  evidence before planning or implementation. It never derives LR or live
  authorization from the board stage or an engineering ledger.
disable-model-invocation: true
---

# CDB control intake

## Zweck und Grenze

Erzeuge vor Planung oder Implementierung einen belegten Control-Snapshot.
Der Skill ist read-only: kein GitHub-, Repo-, DB-, Runtime- oder Live-Write.
`CURRENT_STATUS.md` ist nur Engineering-Ledger; `CONTROL_REGISTER` ist
Board-/Stage-Kontext; allein die LR-SSOT bestimmt das LR-Verdikt.

## Pflichtquellen in dieser Reihenfolge

1. `docs/runbooks/CONTROL_REGISTER.md`
2. GitHub Issue `#1445` live
3. Der neueste fuer den aktuellen Control-Stand maßgebliche Kommentar in `#1445`.
   Wenn #1445 eine Rebaseline oder Kommentar-Entwertung anordnet, ist diese
   Anordnung maßgeblich; alte Weekly-/Bot-/Report-Kommentare sind kein Auftrag.
4. GitHub Issue `#1492` live, ausschließlich als Board-/`trade-capable`-Kontext
5. `CURRENT_STATUS.md` als Ledger, niemals als Live-SSOT
6. `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` als LR-SSOT
7. Für den Scope relevante offene Issues/PRs live

## Ablauf

1. Lies jede Pflichtquelle und erfasse Quelle, Abrufzeit, Aussage und Grenzen.
2. Trenne die drei Statusklassen explizit:
   - **Board stage:** nur Board-/Stage-System aus Register und #1492.
   - **Engineering:** GitHub-live und Repo-Evidence nach Truth Order; Ledger
     bleibt als Ledger gekennzeichnet.
   - **LR verdict:** ausschließlich die LR-SSOT. `trade-capable` bedeutet
     weder LR-Go noch Echtgeld-/Live-Go.
3. Bestimme den maßgeblichen #1445-Stand. Ist nicht belastbar feststellbar,
   behaupte keine aktuelle Priorität und setze `HOLD_CONTROL_COMMENT_AMBIGUOUS`.
4. Prüfe relevante offene PRs/Issues live. Fehlt notwendige GitHub-Evidence,
   setze `HOLD_GITHUB_LIVE_EVIDENCE_MISSING`; keine Live-Wahrheit erfinden.
5. Vergleiche Register, Live-Evidence, Ledger und LR-SSOT. Widersprüche werden
   nach Statusklasse getrennt ausgegeben; eine nicht trennbare Aussage setzt
   `HOLD_CONTROL_TRUTH_CONFLICT`.
6. Gib nur bei vollständigem Snapshot den kleinsten sinnvollen nächsten Slice
   aus. LR bleibt fail-closed `NO-GO`, wenn die LR-SSOT unklar oder nicht lesbar ist.

## Stop-Regeln

- Pflicht-Canon fehlt oder ist nicht lesbar: `HOLD_REQUIRED_CANON_MISSING`.
- #1445, der maßgebliche Kommentar, #1492 oder relevante GitHub-Live-Evidence
  fehlt: `HOLD_GITHUB_LIVE_EVIDENCE_MISSING`.
- Board-/Ledger-Signal würde als LR-/Live-Go gelesen: `HOLD_STATUS_CLASS_MIXUP`.
- Widerspruch lässt sich nicht sauber Board, Engineering oder LR zuordnen:
  `HOLD_CONTROL_TRUTH_CONFLICT`.
- Ein HOLD enthält Quellen, fehlende Evidence und den nächsten read-only Schritt;
  er enthält keine erfundene Priorität oder Freigabe.

## Ausgabevertrag

```md
Control-Snapshot
- Board stage: <value | HOLD>
- LR verdict: <value | HOLD>
- Engineering-/operativer Fokus: <live evidence; ledger separat markiert>
- Relevante offene GitHub-PRs/Issues: <Liste | keine | HOLD>
- Rote Checks, Widersprüche, Unsicherheiten: <Liste | keine>
- Nächster Slice: <kleinster Slice | HOLD-Code + read-only next step>

Truth-Boundaries
- Board stage ist keine LR- oder Echtgeld-Freigabe.
- CURRENT_STATUS.md ist Ledger, nicht Live-SSOT.
- #1492 liefert nur Stage-Kontext.
```

## Smoke

Führe nach einer Änderung aus:

```powershell
pytest -q tests/unit/agents/test_control_intake_skill_contract.py
python tools/validate_skill_surface_mirror.py --skill cdb-control-intake
git diff --check
```

Ein PASS beweist den Dokument-/Mirror-Vertrag; die konkrete Session-Wahrheit
bleibt erst nach ihren Live-Reads belegt.
