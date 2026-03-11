# Codex Batch 05 Ideas (2025-12-31)

Ziel
- 72h Test-Reife der Engine (Block 4 aus C:\Users\janne\Desktop\ganzer plan.txt).

Issue-Reihenfolge (logische Abfolge + Abhaengigkeiten)
1) #413 - CI billing limit (harte Voraussetzung fuer CI Evidence)
2) #355 - CI/CD back to green (required checks stabilisieren)
3) #224 - order_results publish (E2E Grundpfad)
4) #229 - test harness cursor bug (E2E Stabilitaet)
5) #230 - guard cases TC-P0-003/004 (Risiko-Guards)
6) #162 - performance tests nutzen (Baselines)
7) #159 / #172 - 72h Validation + Operational Readiness

Notizen / Annahmen
- #229: _count_rows im Repo nicht gefunden (Issue evtl. veraltet oder Datei lokal).
- #413: Admin/Billing Action noetig, sonst keine CI Evidence moeglich.
- #355: Viele failing Checks; Bedarf an Priorisierung der required Checks.

Naechste Schritte (dieses Batch)
- PR fuer #224 oeffnen und Issue verlinken.
- Issue-Kommentare fuer #413, #229, #230, #172, #355 mit aktuellem Status/Plan.
- Neue Issue: 72h Test-Runbook + Akzeptanzkriterien (nicht redundant zu #172).
