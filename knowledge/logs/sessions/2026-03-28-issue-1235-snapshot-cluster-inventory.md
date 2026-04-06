# Session Log — 2026-03-28 — Issue #1235 Snapshot Cluster Inventory

## Ziel

Snapshot-Navigationsdrag reduzieren, aktive von eingefrorenen Quellen trennen, Low-Visibility-Cluster klassifizieren.

## Durchgeführt

### 1. Analyse
- `docs/archive/docs_hub_snapshot/` vollständig inventarisiert (635 Dateien)
- `infrastructure/scripts/docs_hub_rag_adapter.py` direkt gelesen → Compat-Annahmen in `DOCS_HUB_DELETE_READINESS.md` überzeichnet; Snapshot ist Fallback-only, Adapter nutzt Top-Level-Dirs
- Aktive Referenzen auf alle 4 Low-Visibility-Cluster geprüft: keine produktiven Abhängigkeiten (`.worktrees/`-Treffer = tote Worktrees)
- Guard `docs-conflict-guard.yml` bestätigt: Snapshot bereits vollständig ausgeschlossen

### 2. Delta (Commit 1240f8e, PR #1295)
- `.gitattributes`: `docs/archive/docs_hub_snapshot/** linguist-documentation=true`
- `docs/meta/SNAPSHOT_CLUSTER_INVENTORY.md` (neu): 7 Cluster klassifiziert
- `docs/archive/docs_hub_snapshot/README.md`: Abschnitt „Low-Visibility Review Targets" ergänzt

### 3. Issue-Kommentar
- Unter #1235 gepostet: issuecomment-4148622869
- Sprach-Schärfung durch Maintainer: keine absoluten GitHub-Verhalten-Behauptungen, kein „das ist falsch", kein „jederzeit" für Prune-Entscheidungen

## Kein Eingriff in

- Runtime, Core, Services — unberührt
- Bestehende Guards — unverändert
- Snapshot-Inhalt — keine Datei wurde gelöscht oder verschoben

## Status

- PR #1295 gemerged 2026-03-28T19:10:36Z, Squash-Commit b2ebb41
- Issue #1235: geschlossen nach Merge von PR #1295
- Copilot-Review-Threads (2): resolved via GraphQL vor Merge
- policy-gate initial FAIL wegen .gitattributes → label `manual-approval` gesetzt → PASS

## Restunsicherheiten

- `linguist-documentation=true` ist kein harter Garant für vollständige GitHub-Search-Unterdrückung
- Prune-Entscheidung für die 4 Low-Visibility-Cluster (~100 Dateien) bleibt separater zukünftiger Schritt
