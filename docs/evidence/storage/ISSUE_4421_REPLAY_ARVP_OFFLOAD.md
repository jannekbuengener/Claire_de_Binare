# Issue #4421 — Replay/ARVP Bulk-Offload Evidence

Status: Copy-/Integritätsnachweis und versionierbarer Consumer-Cutover

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

## Cutover-Mechanismus

Die 66 relevanten Consumer-Pfade werden ohne Verdrängen versionierter Inhalte
behandelt:

- 49 konfliktfreie Pfade stehen im versionierten Inventory
  `tools.storage.replay_arvp_storage.JUNCTION_CUTOVER_ROOTS`. Der explizite
  Helper `apply_replay_arvp_junction_cutover()` erzeugt ausschließlich diese
  Junctions, nur zu `Y:\CDB-Storage\replay-arvp`, und verweigert fehlende
  Ziele oder jede vorhandene Nicht-Junction.
- Die 17 Canon-Konflikte bleiben als versionierte Repo-Verzeichnisse erhalten.
  Opt-in-Consumer verwenden
  `resolve_replay_arvp_consumer_path()` bzw.
  `resolve_replay_arvp_payload_path()`; bei gesetztem
  `CDB_BULK_STORAGE_ROOT=Y:\CDB-Storage` beziehen sie Bulk-Payload aus
  `Y:\CDB-Storage\replay-arvp`. Ohne Opt-in bleibt allein der versionierte
  Canon-Pfad aktiv.
- Die beiden PostgreSQL-HOLD-Bäume sind weder im Junction-Inventory noch im
  Resolver-Scope enthalten.

Der Resolver akzeptiert nur die 17 klassifizierten Canon-Roots und lehnt
fehlende Roots, `E:`, `Y:\Worktrees`, Traversal und nicht verwaltete Pfade
fail-closed ab. Es gibt keinen E:-Fallback und keine Erzeugung, Kopie,
Verschiebung oder Löschung von Payload durch den Resolver.

## Consumer- und Layout-Nachweis

- Junction-Apply im sauberen #4421-Worktree: `0` neu erzeugt; alle 49
  deklarierten Junctions bereits auf Y:, kein E:-Target.
- 17/17 deklarierte Canon-Bulk-Roots unter
  `Y:\CDB-Storage\replay-arvp` vorhanden.
- Strategy-Replay-Default löst nach
  `Y:\CDB-Storage\replay-arvp\replay_reports` auf.
- Paper-Reference-Window-Default löst nach
  `Y:\CDB-Storage\replay-arvp\paper_reference_windows\paper_reference_window.json`
  auf.
- Price-Policy-Replay löst seine Calibration-, Recheck-, Candle- und
  Paper-Reference-Eingaben nach Y: auf; alle vier Ziel-Dateien sind vorhanden.
- Fokussierte Tests: `121 passed`; gezielter Ruff-Check und
  `git diff --check`: PASS.

## Safety Boundaries

- Kein Bulk unter `Y:\Worktrees`.
- Keine `market_data`-Änderung; diese gehört zu #4420.
- Keine Docker-Volumes, Runtime-, Live- oder Echtgeld-Aktionen.
- Die E:-Quelle wird in diesem Schritt nicht gelöscht: Der befristete
  Rückrollbestand bleibt erhalten, bis der gemergte Cutover in einem späteren,
  ausdrücklich verifizierten Cleanup-Schritt die Source-Retention entscheidet.
