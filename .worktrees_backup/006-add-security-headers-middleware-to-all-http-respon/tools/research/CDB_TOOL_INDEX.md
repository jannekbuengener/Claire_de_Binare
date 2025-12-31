# CDB Code Tools Index (Stdlib-only, Read-Only)

## CI/CD & DevOps
- cdb_import_cycle_scanner.py — Import-Zyklen via AST, Exit 1 bei Zyklen
- cdb_architecture_boundary_checker.py — Cross-Package-Import-Heuristik, Exit 1 bei Verstößen
- cdb_regex_sniper.py — Regex-Suche (konfigurierbare Patterns/Exts), Exit 1 bei Treffern
- cdb_keyword_heatmap.py — Keyword-Zählung (TODO/FIXME/HACK), Exit 0
- cdb_argument_parser_mapper.py — Argparse-Parser/Argumente inventarisieren, Exit 0
- cdb_action_mask_validator.py — Heuristik für Action-Mask-Nutzung, Exit 1 bei Funden
- cdb_policy_similarity_tracker.py — Token-Jaccard für zwei Pfade, Exit 0

## Codequalität & Struktur
- cdb_low_level_antipattern_scanner.py — eval/exec/bare except/import *, Exit 1 bei Funden
- cdb_missing_docstring_finder.py — Fehlende Docstrings, Exit 1 bei Funden
- cdb_long_function_analyzer.py — Lange Funktionen/Methoden > Threshold, Exit 1 bei Funden
- cdb_duplicate_code_detector.py — Duplikate via Sliding-Window-Hash, Exit 1 bei Funden
- cdb_missing_init_finder.py — Paket-Verzeichnisse ohne __init__.py, Exit 1 bei Funden
- cdb_dead_comment_scanner.py — Auskommentierter Altcode/TODO remove, Exit 1 bei Funden
- cdb_complexity_threshold_report.py — Zu viele Funktionen/Klassen pro Datei, Exit 1 bei Funden
- cdb_big_object_finder.py — Große Literale (Listen/Dicts/Strings), Exit 1 bei Funden
- cdb_constant_usage_matrix.py — Numerische Konstanten & Vorkommen, Exit 1 bei Funden
- cdb_module_size_profiler.py — Zeilen/Funktionen/Klassen je Datei, Exit 0
- cdb_comment_density_auditor.py — Kommentarquote je Datei, Exit 0

## Repo-Übersicht & Inventare
- cdb_filetype_inventory.py — Dateitypen zählen (Top-N), Exit 0
- cdb_folder_structure_snapshot.py — ASCII-Baum der Struktur, Exit 0
- cdb_top10_largest_files.py — Größte Dateien, Exit 0
- cdb_empty_file_detector.py — Leere/kleine Dateien, Exit 1 bei Funden
- cdb_mixed_encoding_detector.py — Nicht-UTF8-Dateien, Exit 1 bei Funden
- cdb_file_similarity_cluster.py — Identische Dateien clustern, Exit 1 bei Clustern
- cdb_timestamp_report.py — Älteste/neueste Dateien, Exit 0

## Daten & Reports
- cdb_data_dir_auditor.py — data/… Verzeichnisse: große/temp/nicht-UTF8/Überfüllung, Exit 1 bei Issues
- cdb_json_schema_extractor.py — Best-Effort JSON-Shape, Exit 1 bei Fehlern
- cdb_feature_outlier_scanner.py — Ausreißer in numerischen JSON/CSV/NDJSON, Exit 1 bei Ausreißern/Fehlern
- cdb_misplaced_config_finder.py — Config-Dateien außerhalb erwarteter Pfade, Exit 1 bei Funden
- cdb_risk_profile_mapper.py — Risk-Profile-/Constraint-Dateien (JSON; YAML stub), Exit 1 bei Fehlern

## Nutzung (alle Tools)
- Aufruf: `python tools/<tool>.py [--json]` (ggf. zusätzliche Optionen pro Tool)
- Alle Tools sind read-only und verwenden nur die Python-Standardbibliothek.

