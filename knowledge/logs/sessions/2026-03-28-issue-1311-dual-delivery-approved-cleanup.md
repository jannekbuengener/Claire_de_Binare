# Session Log — 2026-03-28 — Issue #1311: Dual DELIVERY_APPROVED.yaml Cleanup

## Ziel

Doppelte `DELIVERY_APPROVED.yaml`-Dateien bereinigen, damit genau eine kanonische Delivery-Gate-Datei existiert.

## Befund

- `governance/DELIVERY_APPROVED.yaml` — CI-aktiv, vom Workflow `delivery-gate.yml` gelesen
- `knowledge/governance/DELIVERY_APPROVED.yaml` — orphaned, von keinem Workflow gelesen, abweichende Inhalte (`approved_at` 2026-01-05 vs. 2025-12-28, falscher `status: canonical`-Claim)
- Alle Referenzen auf den `knowledge/governance/`-Pfad lagen in `docs/archive/docs_hub_snapshot/` (eingefrorener Snapshot, nicht aktiv)

## Canon-Entscheidung

`governance/DELIVERY_APPROVED.yaml` ist die einzige kanonische, CI-aktive Delivery-Gate-Datei.

## Geänderte Dateien

- `knowledge/governance/DELIVERY_APPROVED.yaml` — gelöscht (orphaned duplicate)
- `knowledge/GOVERNANCE_QUICKREF.md` — Duplikat-Hinweis und `#1311`-Verweis entfernt; Section 2 auf single authoritative gate file aktualisiert

## Durchgeführte Schritte

1. Beide Dateien verglichen, Workflow-Referenz verifiziert
2. `git rm knowledge/governance/DELIVERY_APPROVED.yaml`
3. `GOVERNANCE_QUICKREF.md` bereinigt
4. Commit auf Branch `fix/1311-dual-delivery-approved-cleanup`
5. Push + PR erstellt
6. Issue-Kommentar + Close

## Commit

- Hash: `c2d53d1`
- Message: `chore(governance): remove duplicate DELIVERY_APPROVED.yaml from knowledge/governance/ (#1311)`

## Status

- PR: #1313 (offen, docs-only)
- Issue: #1311 geschlossen
