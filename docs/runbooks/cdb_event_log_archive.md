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
Plan fail-closed. Quelle und Archivziel müssen außerdem vollständig disjoint
sein; Gleichheit oder eine Verschachtelung in beide Richtungen blockiert den
Plan. Auch jede einzelne Candidate-Datei wird vor Metadaten- oder Hash-Zugriff
auf Reparse-/Symlink-Eigenschaften geprüft. Ein noch nicht provisioniertes
`logs\\events`-Ziel bleibt read-only planbar, erscheint aber als
`HOLD_DESTINATION_ROOT_REQUIRED` und blockiert jeden späteren Apply. Ein
vorhandenes Ziel mit abweichendem Hash ist `HOLD`; ein identisches vorhandenes
Ziel ist als Resume-Fall zulässig.

## Apply-Vertrag

`python -m tools.storage.log_archive apply --plan <plan.json>
--expected-fingerprint <sha256> --evidence-output <result.json>` verarbeitet
nie einen neu bestimmten Scope: ausschließlich `ARCHIVE_CANDIDATE`-Einträge des
gebundenen Plans. Der erwartete Fingerprint ist Pflicht und muss sowohl dem
eingebetteten Plan-Fingerprint als auch der kanonischen Serialisierung des
Plans entsprechen. Abweichungen stoppen vor jedem Copy.

Ein gebundener Plan mit `hold_reasons`, fehlendem Ziel beim Planning oder einem
`HOLD`-Entry bleibt dauerhaft nicht applybar; eine spätere Umgebungsänderung
hebt den HOLD nicht auf. Dafür ist ein frischer Plan mit neuem Fingerprint
notwendig. Ein einzelner `HOLD`-Entry blockiert den gesamten Apply vor Copy oder
Delete und bleibt in der maschinenlesbaren Evidence sichtbar.

Vor Copy, nach Copy und unmittelbar vor Source-Delete werden Pfad, Größe und
SHA-256 geprüft. Copy, Destination-Verify und Delete bleiben pro Datei strikt
getrennt. Ein vorhandenes, exakt gleiches Ziel ist ein zulässiger Resume-Fall;
ein abweichendes oder nicht reguläres Ziel ist `HELD_DESTINATION_COLLISION`.
Source-, Größen-, Hash-, Traversal- oder Reparse-Drift hält den Apply an und
löscht die Quelle nicht. `_archive_*`, `_quarantine`, absolute oder `..`-Pfade
sowie Ziele außerhalb des kanonischen `logs/events`-Subtrees werden nie
ausgeführt. Die konkrete Destination-Datei selbst wird vor Resume oder Copy auf
Reparse-/Symlink-Eigenschaften geprüft, einschließlich dangling Links.

Der Apply schreibt atomar maschinenlesbare Evidence. Schema
`cdb.log-archive-apply-result/v1` enthält mindestens Schema, Issue,
Plan-Fingerprint, Quelle/Ziel, Start/Ende, Plan-/Copy-/Resume-/Verify-/Delete-
und Hold-Zähler samt Bytes, Ergebnis und Entry-Liste. Jeder Entry enthält
relativen Pfad, erwartete Größe/Hash, Zielpfad, Disposition,
Destination-Verifikation, Source-Delete und Failure-Reason.

Der Evidence-Ausgabepfad muss vor dem ersten Journal-Write vollständig disjoint
von Source- und Archive-Destination-Baum sein. Er darf weder Datenpfade
aliasieren noch innerhalb eines Datenbaums liegen oder einen Datenbaum als
Unterpfad enthalten.

Vor der ersten Datenmutation muss der Runner ein Journal mit
`APPLY_STARTED` atomar schreiben. Vor jedem Delete wird `DELETE_PENDING`
persistiert, danach `APPLY_IN_PROGRESS`; erst der Abschluss trägt
`APPLY_COMPLETED`. Scheitert die Journal-Initialisierung, beginnt kein Apply.
Scheitert ein späterer Journal-Write, stoppt der Runner vor weiteren Deletes;
das zuletzt persistierte Journal bleibt als Grenze der Audit-Evidence erhalten.

Der spätere kanonische Evidence-Pfad lautet
`Y:\\CDB-Storage\\evidence\\issue-4422\\archive_apply_result.json`; diese
Session erzeugt ihn nicht und führt keinen realen lokalen Apply aus.

## Nicht-Ziele

- Keine automatische Archivierung von `paper_trading_*.log`.
- Keine Rotation laufender Writer oder heutiger/hot Dateien.
- Keine Docker-/Compose-Mutation, keine Junctions und kein Fallback auf D:, E:\
  oder `Y:\Worktrees`.
