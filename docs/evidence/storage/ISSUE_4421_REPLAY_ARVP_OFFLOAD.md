# Issue #4421 — Replay/ARVP Bulk-Offload Evidence

Status: Copy- und Integritätsnachweis vor Junction-Retargeting

## Scope-Klassifikation

| Klasse | Bäume | Bytes | Behandlung |
|---|---:|---:|---|
| `OFFLOAD` | 67 | 429,267,174 | Nach `Y:\CDB-Storage\replay-arvp` kopiert und verifiziert. |
| `HOLD` | 2 | 1,245,282,684 | `postgres_restore_3600_work` und `postgres_rebuild_3600_20260701_024237` bleiben unverändert auf E:. |

`HOLD`-Bäume werden weder gelöscht noch retargetet; ihre operative
Klassifikation liegt außerhalb dieses Issue-Slices.

## Integritätsnachweis

- Quelle: `E:\CDB_artifacts`
- Ziel: `Y:\CDB-Storage\replay-arvp`
- Dateien: 15,143 auf Quelle und Ziel
- Bytes: 429,267,174 auf Quelle und Ziel
- SHA-256-Manifeste: identischer Fingerprint
  `de09b87befd2adbd5cb2099169b8494bbb44047256907bb67c14ed89a86c3fe9`
- Vergleich: keine fehlenden, zusätzlichen oder abweichenden Dateien
- Persistente Maschinen-Evidence:
  `Y:\CDB-Storage\evidence\issue-4421\offload_manifest_compare.json`

## Safety Boundaries

- Kein Bulk unter `Y:\Worktrees`.
- Keine `market_data`-Änderung; diese gehört zu #4420.
- Keine Docker-Volumes, Runtime-, Live- oder Echtgeld-Aktionen.
- E:-Quellen und Repo-Junctions bleiben bis zum dokumentierten Consumer-Smoke
  unverändert.
