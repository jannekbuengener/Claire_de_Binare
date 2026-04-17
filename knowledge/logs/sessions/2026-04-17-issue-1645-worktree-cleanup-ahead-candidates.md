# Session Log: #1645 `.worktrees/*` ahead-Kandidaten bereinigt

**Date:** 2026-04-17
**Issue:** [#1645](https://github.com/jannekbuengener/Claire_de_Binare/issues/1645) — [HARDENING][GIT] Carefully disentangle local Git/worktree state and reduce branch sprawl
**Scope:** Alle 6 `.worktrees/*`-Branches mit `ahead > 0` einzeln geprüft und bereinigt
**Result:** `.worktrees/*`-Scope vollständig abgeschlossen; 245 → 239 Branches, 7 → 1 Worktrees

---

## Methode

Jeder Kandidat als eigenständiger Slice mit festem Ablauf:
1. `git worktree list` + `git branch -vv` + `git branch -r` → Remote live verifikation
2. `git log main..<branch> --oneline` → Commit(s) identifizieren
3. `git log origin/<branch> ^<branch>` → Extra-Commits auf Remote (Sentinel/Jules-Pattern)
4. `git show <commit> --stat` + Inhaltsprüfung gegen main (Blob-Hash oder Diff-Vergleich)
5. Klassifikation: cleanup-ready oder nicht
6. Falls cleanup-ready: `git worktree remove --force` → `git branch -D` → `git push origin --delete`
7. Issue-Kommentar in #1645

---

## Kandidaten-Übersicht

| Branch | Worktree | ahead | Remote | Befund | Ergebnis |
|---|---|---|---|---|---|
| `ci/automerge-jules` | `.worktrees/automerge-jules` | 1 | ja (IN SYNC nach fetch) | Automerge-Workflow stale (Jan 2026 abandoned); Security-Fix-Content (json.dumps + test) auf main via anderen Pfad | bereinigt |
| `ci/627-guardrails` | `.worktrees/627-ci-guardrails` | 1 | ja (remote +1 Sourcery) | Makefile-Targets stale (fehlendes --config), test_import_smoke superseded, e2e.yml SMTP auf main | bereinigt |
| `feature/ci-aggregator` | `.worktrees/ci-aggregator` | 1 | ja (IN SYNC) | CI-Aggregator-Konzept auf main anders umgesetzt; PRs #687/#688 CLOSED | bereinigt |
| `ci/665-planning-lint` | `.worktrees/issue-665` | 2 | ja (IN SYNC) | planning_lint.py blob-identisch auf main (`tools/test_pack/tools/planning/`); Workflow zielt auf obsoletes Docs-Hub-Repo | bereinigt |
| `feature/432-mcp-stack-green` | `.worktrees/mcp-stack-green` | 1 | ja (IN SYNC) | mcp-server-time dep in requirements-mcp.txt auf main; ci.yaml durch ci.yml superseded; .mcp.json nicht mehr getrackt | bereinigt |
| `feature/sdb-after-soak-evidence-fix2` | `.worktrees/sdb-after-soak-fix2` | 1 | ja (IN SYNC) | redis-exporter-Gate auf main als `optional_services` gelöst (3. Architektur); pr_body.txt staler Draft | bereinigt |

---

## Muster / Erkenntnisse

**Konsistenter Dirty-State:**
Alle 6 Worktrees hatten `D .mcp.json` — alte Credential-Datei (`<redacted>` Grafana-Token + `<redacted>` Postgres-Passwort) war committed und dann aus dem Working Tree gelöscht. Pre-existing history exposure, nicht neu. Ursache: `git worktree remove --force` nötig in allen Fällen.

**Batch-Klassifikation Remote-Status unzuverlässig:**
Erste Batch-Klassifikation hatte `ci/automerge-jules` und `ci/627-guardrails` als "kein Remote" eingestuft — beide hatten tatsächlich `origin/*`-Remotes. Lesson: Remote-Status immer live via `git branch -r | grep <branch>` prüfen, nie aus Batch ableiten.

**Jules/Sentinel Sideways-Merge-Pattern:**
`ci/automerge-jules` hatte auf dem Remote einen Extra-Commit: Jules-Bot hatte PR #695 (Security-Fix) direkt in den Feature-Branch gemergt (nicht in main). Commit war nicht via `--is-ancestor main` erreichbar. Content-Vergleich (nicht Ancestry) entscheidend.

**Blob-Hash als Superseding-Beweis:**
`planning_lint.py` in Commit (`tools/planning/`) und auf main (`tools/test_pack/tools/planning/`) hatten identischen Blob-Hash `0fc9a539...` — direkter Beweis für identischen Inhalt trotz unterschiedlicher Pfade.

**`-D` immer nötig:**
Alle Branches haben `ahead > 0` vs. main-Ancestry wegen Squash-Merge-Modell (`required_linear_history=true`). `git branch -d` würde fehlschlagen, `-D` nach Inhaltsprüfung korrekt.

**`pr_body.txt` (untracked):**
`feature/sdb-after-soak-evidence-fix2` hatte `pr_body.txt` untracked — war identisch mit PR #699-Beschreibung, kein Novel-Wert. Mit `--force`-Worktree-Remove entfernt.

---

## Ergebnis

- **Worktrees:** 7 → 1 (nur main)
- **Branches:** 245 → 239
- **Working Tree:** clean
- **#1645 `.worktrees/*`-Scope:** vollständig abgeschlossen

## Offener Restscope #1645

~239 lokale Branches noch nicht klassifiziert. Das ist ein eigenständiger Scope, der separate Inventur/Klassifikationsarbeit erfordert und nicht im Rahmen der Worktree-Einzelslice-Serie abgeschlossen wird.
