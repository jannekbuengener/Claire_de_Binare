# CDB PR Routing and Batch Merge Policy

Status: Canonical
Version: `cdb-pr-routing-policy/v1`
Issue: `#4202`

## 1. Zweck und Autorität

Delivery und Merge sind getrennte Vorgänge. Eine Issue-Session liefert einen
eng begrenzten Slice in den vom PR Router bestimmten PR. Ein eigener PR,
vollständige Fast-CI, `cdb-local-ci` und Merge sind kein Session-Default mehr.

Der Router und der `cdb-pr-steward` sind read-only. Session Lead und Human
Authority entscheiden über Writes, Freeze und Merge. LR bleibt `NO-GO`.

## 2. Pflichtreihenfolge

Vor Plan-Finalisierung, Branch-, Worktree- oder PR-Erstellung:

1. Context Brain Preflight und kanonische Read Order.
2. Live Git-/GitHub-State und Dedupe.
3. `python -m tools.pr_routing route --issue <N>`.
4. Routing-Entscheidung und Evidence dokumentieren.
5. Reservation beziehungsweise Lock prüfen.
6. Erst danach die zugewiesene Arbeitsfläche verwenden.

Unvollständige GitHub-Sicht, 50 oder mehr offene PRs, unbekannte Policy- oder
Marker-Versionen, mehrere kompatible Kandidaten und Lock-Konflikte führen zu
HOLD.

## 3. Routing-Entscheidungen

- `ROUTE_TO_EXISTING_BATCH_PR`
- `ROUTE_TO_EXISTING_DEDICATED_PR`
- `CREATE_NEW_BATCH_PR`
- `CREATE_DEDICATED_PR`
- `HOLD_PR_LOCK_CONFLICT`
- `HOLD_NO_SAFE_ROUTE`

Dedicated gilt für Security, Secrets, DB-Migrationen, Live-Readiness,
Echtgeld-adjacent Governance und unabhängige Risk-/Execution-/Runtime-Verträge.

## 4. Batch-Lanes

| Lane | Validation Profile | Default |
| --- | --- | --- |
| `docs-governance` | `docs-governance-v1` | batch |
| `agent-skills` | `agent-skills-v1` | batch |
| `ci-tooling` | `ci-tooling-v1` | batch |
| `validation-research` | `validation-research-v1` | batch |
| `dependencies` | `dependencies-v1` | batch |
| `runtime-risk` | `runtime-risk-v1` | dedicated oder eng isoliert |

Die Dependencies-Lane ersetzt den Dependabot-Broker aus #4061 nicht.
Pausierte oder blockierte Arbeit, insbesondere #4184/PR #4187, ist nicht
routefähig.

## 5. Kompatibilität

Eine Route ist nur kompatibel bei:

- gleicher Base und Lane,
- explizit kompatiblem Validation Profile,
- `steward_state=accepting_slices`,
- Draft oder ausdrücklich offen für Slices,
- keinem Objective-, Contract- oder Risk-Konflikt,
- vollständigem Lock-Inventar,
- weiterhin reviewbarem kombinierten Diff,
- eindeutiger Closure-Lineage.

Genau ein kompatibler PR wird gewählt. Mehrere Kandidaten führen zu HOLD.

## 6. Marker und Ledger

Batch-PRs enthalten exakt einen Marker:

```text
<!-- cdb-batch-pr:v1
policy_id: cdb-pr-routing-v1
batch_key: <stable-key>
lane: <lane>
base_branch: main
validation_profile: <profile>
merge_mode: batch
steward_state: accepting_slices
objective_key: <objective>
planned_issues: #<N>
contract_keys: <sorted-keys-or-none>
risk_flags: <sorted-flags-or-none>
-->
```

Das Ledger steht unter `## CDB Batch Ledger` und besitzt exakt:

| Issue | Status | Commit | Targeted Validation | Risk Class | Restunsicherheit |
| --- | --- | --- | --- | --- | --- |

Zulässige Statuswerte sind `PLANNED`, `LOCKED`, `SLICE_DELIVERED` und
`MERGE_VERIFIED`. `SLICE_DELIVERED` verlangt einen vollständigen Commit-SHA.
Ledger und `Closes #N` müssen bijektiv sein. Issues bleiben bis Merge offen.

## 7. Dual-Lock

Vor einem neuen PR:

`LOCK_RESERVATION: agent=<agent> issue=#<issue> batch_pr=pending ts=<utc> mode=batch-slice`

Nach Draft-PR-Erstellung auf Issue und PR:

`LOCK: agent=<agent> issue=#<issue> batch_pr=#<pr> ts=<utc> mode=batch-slice`

Nur ein identisches Paar erlaubt Writes. Einseitige, fremde, beschädigte oder
stale Locks blockieren. Handoff erfordert paariges `UNLOCK`; stale Locks werden
nie automatisch übernommen.

## 8. Slice-Handoff

Pflicht:

- issue-spezifische Tests und Contracts,
- Lint/Format für betroffene Dateien,
- `git diff --check`,
- kohärenter Commit und Push,
- Ledger-Update,
- Issue-Kommentar mit PR, Commit, Tests und Restunsicherheit.

Default:

```yaml
full_fast_ci: false
publish_cdb_local_ci: false
merge: false
close_issue: false
status: DONE_SLICE_ADDED_TO_BATCH_PR
```

## 9. Merge-Trigger

- `BATCH_COMPLETE`
- mindestens drei gelieferte Issue-Slices,
- mindestens fünf Kalendertage,
- mindestens 20 Dateien oder `additions + deletions >= 1000`,
- expliziter Dependency-Blocker,
- Security-/Safety-Signal,
- explizites Operator-GO.

Jeder Trigger startet Acceptance bei `COMPLETENESS_REVIEW` und setzt Transport
auf `merge_candidate`. Er autorisiert keinen Merge. Fachliche Freigabe kommt
nur von `cdb-pr-completeness-review` → `MERGE_CANDIDATE`, danach
`cdb-batch-merge-conductor`.

## 10. Finaler Merge-Head

1. `cdb-pr-completeness-review` ausführen; nur bei `MERGE_CANDIDATE` weiter.
2. `cdb-batch-merge-conductor`: PR für neue Slices einfrieren (`FROZEN`).
3. Verlinkte Issues, Ledger und Restunsicherheiten prüfen.
4. Aktuelles `main` integrieren und Base-SHA binden; bei Drift Completeness
   erneut.
5. Kombinierten Diff reviewen.
6. Vollständige Fast-CI auf exakt dem finalen Head.
7. Policy-Gate-Mirror und Publisher-Dry-run.
8. `cdb-local-ci` via Publisher und `gh api` auf exakt diesem SHA.
9. Combined Commit Status live prüfen.
10. Head-/Base-Drift erneut prüfen; Drift invalidiert alle Final-Evidence.
11. Normaler Squash-Merge ohne Admin-Bypass (`cdb-batch-merge-conductor`).
12. Merge-SHA auf `main` verifizieren und nur `SLICE_DELIVERED` Issues schließen
    via `cdb-session-close`.

Keine stale Slice-Evidence, kein Zwischenstands-Publish und kein Fake-Green.
Kein Bypass des Completeness-Gates.

## 11. Machine Policy und Validatoren

- Policy: `config/governance/pr-routing-policy.v1.yaml`
- CLI: `python -m tools.pr_routing`
- Skill-Canon: `docs/skills/cdb-pr-router/SKILL.md`
- Steward: `.cursor/agents/cdb-pr-steward.md`

Die Policy ist deklarativ; GitHub-State und Locks werden ausschließlich live und
read-only über `gh` inventarisiert.

## 12. Grenzen

- Keine Änderung an Branch Protection durch diesen Vertrag.
- Keine Live-, Echtgeld-, Tresor-, Risk- oder Execution-Autorisierung.
- #4061 bleibt separat.
- #4184 und PR #4187 bleiben geparkt und unverändert.
- LR bleibt `NO-GO`.
