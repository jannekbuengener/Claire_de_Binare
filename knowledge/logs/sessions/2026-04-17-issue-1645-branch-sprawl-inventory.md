# Session Log: #1645 Branch-Sprawl-Inventur

**Datum:** 2026-04-17
**Issue:** #1645 — [HARDENING][GIT] Carefully disentangle local Git/worktree state and reduce branch sprawl
**Scope:** Inventur + Klassifikation lokaler Branch-Sprawl (~244 Branches); kein Cleanup
**Status:** Inventur abgeschlossen, Wave-1-Kandidaten identifiziert

---

## Ausgangslage

- PR #1735 gemergt (84a17c31) — `.worktrees/*`-Subscope vollständig abgeschlossen
- 1 Worktree (main only)
- 245 lokale Branches (inkl. main)
- Kein offener PR

---

## Durchgeführte Schritte

1. `git fetch origin --prune` → 2 stale Refs bereinigt:
   - `origin/docs/1645-session-close-20260417`
   - `origin/docs/1645-worktree-cleanup-session-close`
2. Vollständige Branch-Inventur via `git for-each-ref` + `git rev-list --left-right --count`
3. Remote-Branch-Liste nach Prune: 21 Refs (20 non-main)
4. Klassifikation in 4 Klassen mit Sub-Buckets

---

## Klassifikationsergebnis

| Klasse | Anzahl |
|---|---|
| `main` | 1 |
| `tracking-live` | 14 |
| `tracking-origin-main` | 10 |
| `tracking-gone` | 166 |
| `local-only` | 54 |
| **Gesamt** | **245** |

### tracking-gone (166) — Altersverteilung

| Behind | Anzahl |
|---|---|
| ≤ 50 (recent) | 12 |
| 51–200 (medium) | 73 |
| > 200 (old) | 81 |

### local-only (54) — Sub-Klassen

| Sub | Anzahl |
|---|---|
| `backup/*` | 7 |
| `auto-claude/*` + `copilot/*` | 11 |
| `pr-ref` | 7 |
| `reset/from-codex-green` | 1 |
| `other` | 28 |

---

## Root Cause

Squash-Merge-Modell + "delete on merge" löscht Remote-Branch nach PR-Merge,
aber lokaler Branch bleibt immer erhalten. Pro merged PR = 1 verwaister lokaler Branch.
~240 merged PRs → ~166 tracking-gone Branches (plus local-only Restbestand).

---

## Wave-1-Kandidaten (next slice)

4-Branch-Micro-Batch `recent-gone-semantic` (hinter ≤ 10, 1 Commit, semantic name):

| Branch | Behind | Ahead |
|---|---|---|
| `docs/status-mark-1716-merged` | 6 | 1 |
| `fix/security-trixie-digest-1716` | 7 | 2 |
| `docs/status-mark-1717-merged` | 8 | 1 |
| `fix/security-postgres-digest-pin-1717` | 9 | 1 |

Je Branch: Commit-Content-Check + live PR-Verifikation → ggf. `git branch -D`.

---

## Explicit Hold

- `backup/*` (7): intentionale Safety-Nets — kein Auto-Delete
- `reset/from-codex-green` (1, ahead=24): unbekannter Inhalt — explicit hold
- `tracking-live` (14): live Remote — not touch

---

## Issue-Kommentar gepostet

#1645: https://github.com/jannekbuengener/Claire_de_Binare/issues/1645#issuecomment-4268385111
