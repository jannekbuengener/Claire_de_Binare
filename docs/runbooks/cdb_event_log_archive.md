# CDB Event-Log-Archivierungsvertrag

Status: Contract für Issue #4422. Dieser Vertrag definiert ausschließlich den
deterministischen Plan- und späteren Apply-Pfad für historische Event-Logs.
Er ändert weder Compose-Bind-Mounts noch Runtime-Writer und autorisiert kein
Live- oder Echtgeldverhalten.

## Geltungsbereich

- Quelle: `logs/events` im Repository-Arbeitsbaum.
- Ziel: `Y:\CDB-Storage\logs\events`, ausschließlich über den opt-in
  `CDB_BULK_STORAGE_ROOT=Y:\CDB-Storage` und
  `tools.storage.bulk_storage_contract`.
- Kandidatenname: exakt `events_YYYYMMDD.jsonl`.
- Hot-Window: 30 Kalendertage vor dem explizit injizierten `as_of_utc`.

Eine Datei ist nur dann `ARCHIVE_CANDIDATE`, wenn ihr Datum strikt älter als
`as_of_utc.date() - 30 Tage` ist. Dateien im Hot-Window einschließlich der
heutigen Datei sind `KEEP_HOT`. Unbekannte Namen, `_quarantine`, `_archive_*`
und `paper_trading_*.log` werden als `EXCLUDE_UNKNOWN` ausgewiesen und nie
archiviert.

## Plan-Vertrag

`python -m tools.storage.log_archive plan` ist strikt read-only: weder Quelle
noch Ziel werden erzeugt, kopiert, verschoben oder gelöscht. Der Plan enthält
pro Eintrag relativen Pfad, Größe, SHA-256, UTC-LastWrite und Klassifikation
sowie `as_of_utc`, Cutoff und einen kanonisch serialisierten
`plan_fingerprint`.

Fehlt der kanonische Bulk-Root, ist er nicht `Y:\CDB-Storage`, liegt er unter
`Y:\Worktrees`, oder enthält Quelle/Ziel eine Reparse-Komponente, endet der
Plan fail-closed. Ein noch nicht provisioniertes `logs\\events`-Ziel bleibt
read-only planbar, erscheint aber als `HOLD_DESTINATION_ROOT_REQUIRED` und
blockiert jeden späteren Apply. Ein vorhandenes Ziel mit abweichendem Hash ist
`HOLD`; ein identisches vorhandenes Ziel ist als Resume-Fall zulässig.

## Apply-Gate (nicht Teil von #4422 v1)

Ein späterer, separat autorisierter Apply darf erst nach erneutem Plan, stabiler
Quelle und vollständigem Copy-Verify handeln: Größe und SHA-256 von Quelle und
Ziel müssen übereinstimmen. Jede nach Planung veränderte Quelle, jeder
Hash-Mismatch oder jede Zielkollision mit abweichendem Inhalt blockiert. Ein
Source-Unlink ist erst danach zulässig. Dieser v1-Slice bietet keinen
Copy/Delete-Apply.

## Nicht-Ziele

- Keine automatische Archivierung von `paper_trading_*.log`.
- Keine Rotation laufender Writer oder heutiger/hot Dateien.
- Keine Docker-/Compose-Mutation, keine Junctions und kein Fallback auf D:, E:
  oder `Y:\Worktrees`.
