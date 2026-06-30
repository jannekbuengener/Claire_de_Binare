# Unified GitHub Status Snapshot

## Executive Summary

`Unified GitHub Status Snapshot` ist ein docs-only Vorschlag fuer eine breite,
read-only GitHub-Statusflaeche fuer CDB und das spaetere Modusmono-Portfolio.
Das Feature soll wiederkehrende manuelle Sweeps ueber Issues, Pull Requests,
Reviews, Checks, Actions-Runs, Logs, Labels, Branch-/Merge-Lage und ProjectV2
durch einen belastbaren Snapshot ersetzen.

Leitprinzip:

- Broad read, narrow write.
- Fuer den Snapshot gilt ein breites Read-only-Bundle.
- Write-, Admin-, Secret- oder Runtime-Rechte gehoeren nicht in das MVP.
- ProjectV2 und Checks muessen auth-seitig ehrlich modelliert werden.
- Fine-grained PAT ist hilfreich, aber keine vollstaendige Universalloesung.
- Langfristiges Zielbild ist eher ein GitHub App Read-Modell als eine immer
  staerker user-gebundene Token-Loesung.

## Praktische Bedeutung fuer Jannek / Modusmono / CDB

### Fuer Jannek

Heute verteilt sich der Live-Status ueber mehrere Klick- und CLI-Pfade:

- `gh issue view`
- `gh pr list`
- `gh pr view`
- `gh pr checks`
- `gh run view`
- `gh project view`

Das kostet Zeit, fuehrt zu unvollstaendigen Live-Bildern und erhoeht das Risiko,
dass Reviews, rote Checks, fehlende Labels oder Project-Abweichungen uebersehen
werden.

### Fuer CDB

Ein Snapshot verbessert:

- Repo-/PR-/Issue-Live-Status vor Session-Start
- Evidence und Auditierbarkeit von Statusaussagen
- Erkennung von Merge-Blockern und stale Checks
- Dedupe- und Follow-up-Entscheidungen
- Trennung von read-only Statusaufnahme und spaeterer Write-Automation

### Fuer Modusmono

Das gleiche Muster ist portfoliofaehig:

- mehrere Repos in einem einheitlichen Statusmodell
- org- oder user-weite ProjectV2-Reconciliation
- priorisierte Management-Sicht fuer offene Arbeit, Blocker und Drift

## Feature-Ziel

Ein Agent soll mit einem einzigen Snapshot erkennen koennen:

- welche Issues offen sind und welche davon relevant oder doppelt wirken
- welche PRs offen, blockiert oder merge-ready sind
- welche Reviews fehlen oder blockieren
- welche Checks rot, pending oder stale sind
- welche Actions-Runs fehlgeschlagen sind und welche Logs relevant sind
- welche Labels fehlen oder inkonsistent sind
- ob eine ProjectV2-Reconciliation noetig ist
- wie die aktuelle Rate-Limit-Lage aussieht

## Welche GitHub-Flaechen der Snapshot abdeckt

Die Zielabdeckung fuer Phase 1 ist bewusst breit read-only:

| Flaeche | Primär | Zweck |
|---|---|---|
| Repo-Metadaten | REST | Repo, Default-Branch, Sichtbarkeit, Basis-Kontext |
| Issues | GraphQL oder REST | offene Issues, Labels, Assignees, Updated-Status |
| Pull Requests | GraphQL oder REST | offene PRs, Merge-Lage, Head/Base, Draft-Status |
| Reviews | GraphQL oder REST | Review-Blocker, fehlende Reviews, `REQUEST_CHANGES` |
| Review-Kommentare | REST | detailierte Review-Findings je PR |
| Checks | GraphQL primär, REST fallback | `statusCheckRollup`, Check-Runs, Check-Suites |
| Commit Statuses | REST | kombinierte Statussicht je Ref als Fallback/Ergaenzung |
| Actions workflow runs | REST | fehlgeschlagene Runs, Jobs, Logs, Attempts |
| Labels | REST | fehlende oder inkonsistente Label-Lage |
| Branch-/Merge-Lage | GraphQL oder REST | merge-ready, blocked, behind, clean |
| Contents | REST | optional fuer Repo-nahe Surface-Checks |
| ProjectV2 | GraphQL primär, ggf. REST ProjectsV2 | Board-/Portfolio-Reconciliation |
| Rate Limits | REST + Response-Header | Budgetlage, Backoff-Steuerung |

## GraphQL-vs-REST-Entscheidung

### Entscheidung

- GraphQL v4 ist die Primaerflaeche fuer zusammenhaengende Management-Snapshots.
- REST bleibt Pflicht fuer Actions-Runs, Jobs, Logs, Labels, Commit Statuses,
  Contents, Rate-Limits und als Fallback fuer einzelne Flächen.

### Warum GraphQL primaer

GitHub beschreibt die GraphQL API selbst als praeziser und flexibler als REST.
Fuer Snapshot-Sichten ist das entscheidend, weil mehrere verbundene Sichten in
einer Query zusammengezogen werden koennen, statt viele Einzelschritte zu
verketten.

GraphQL ist besonders passend fuer:

- `issue`
- `pullRequest`
- Reviews
- `statusCheckRollup`
- Branch-/Merge-Signale
- `projectV2`

### Warum REST zwingend bleibt

REST ist fuer mehrere Flächen klarer oder praktisch stabiler dokumentiert:

- Actions workflow runs
- workflow jobs
- run logs
- labels
- commit statuses
- contents
- rate limits

### Praktische Umsetzung fuer das MVP

- CLI-Prototyp auf Basis von `gh api graphql` und `gh api repos/...`
- GraphQL-Query-Dateien fuer zusammenhaengende Snapshot-Bloecke
- REST-Calls fuer Actions, Labels, Statuses, Logs und Rate-Limits
- JSON + Markdown Output aus einem read-only Sammellauf

## Read-only Permission Bundle

### Leitlinie

Das Snapshot-MVP ist absichtlich nicht mikroskopisch scopt. Der Mehrwert liegt
in einer belastbaren breiten Sicht, nicht in einem unterdimensionierten Token,
der schon bei ProjectV2, Checks oder Security-Teilflaechen blind wird.

### Snapshot-MVP Bundle

Empfohlenes Read-only Bundle:

- `Metadata: read`
- `Contents: read`
- `Issues: read`
- `Pull requests: read`
- `Actions: read`
- `Checks: read`
- `Commit statuses: read`
- `Projects: read` beziehungsweise `read:project`, wenn ProjectV2 Teil des
  Snapshots ist

### Begruendung je Permission

| Permission | Warum sie im Snapshot enthalten ist |
|---|---|
| `Metadata: read` | Repo-Grunddaten sind Basiskontext jeder Snapshot-Erzeugung. |
| `Contents: read` | Ermoeglicht Repo-nahe Referenzchecks und optionales Surface-Crosscheck. |
| `Issues: read` | Offene Issues, Dedupe-Suche, Label-/Milestone-/Assignee-Kontext. |
| `Pull requests: read` | Offene PRs, Review-Lage, Merge-Kontext, Head/Base-Sicht. |
| `Actions: read` | Workflow-Runs, Jobs, Logs, Pending Deployments, Approvals. |
| `Checks: read` | Check-Runs/Check-Suites fuer Status- und Gate-Sicht. |
| `Commit statuses: read` | Fallback und Ergaenzung fuer kombinierte Ref-Statussicht. |
| `Projects: read` / `read:project` | ProjectV2-Reconciliation fuer Board-/Portfolio-Sicht. |

### Bekannte auth-seitige Luecken

#### ProjectV2 / `read:project`

ProjectV2 ist kein theoretischer Wunsch, sondern operative Snapshot-Flaeche.
In einer Live-Pruefung in diesem Repo schlug `gh project view 8 --owner
jannekbuengener` mit fehlendem `read:project` fehl. Deshalb muss das Dokument
ProjectV2-Read klar als eigene Voraussetzung markieren.

#### Fine-grained PAT ist nicht vollstaendig

GitHub dokumentiert mehrere relevante Luecken fuer fine-grained PATs:

- fine-grained PATs koennen laut PAT-Doku nicht die Checks API nutzen
- fine-grained PATs koennen laut PAT-Doku keine user-owned Projects abdecken
- fine-grained PATs koennen laut PAT-Doku nicht mehrere Organisationen auf
  einmal abdecken

Folge:

- fine-grained PAT ist fuer Teile des Snapshot gut geeignet
- es ist aber keine ehrliche Universalloesung fuer den vollen Snapshot
- fuer ProjectV2 und Checks muss die Auth-Realitaet explizit modelliert werden

### Auth-Profile nach Reifegrad

| Profil | Eignung | Bewertung |
|---|---|---|
| bestehende `gh` Session | gut fuer lokale Ein-Repo-Snapshots | kurzfristig praktikabel |
| fine-grained PAT | gut fuer breite REST-read Faelle, aber mit Checks/Projects-Luecken | nur eingeschraenkt |
| classic PAT | technisch breiter, aber user-gebunden und grober | nur bewusst und begrenzt |
| GitHub App | bestes spaeteres Zielbild fuer stabile breite Read-Sicht | Zielarchitektur |

## Optionales Security Read Bundle

Dieses Bundle gehoert nicht zwingend ins erste Snapshot-MVP, aber ist fuer einen
Security Snapshot sinnvoll:

- `Code scanning alerts: read`
- `Dependabot alerts: read`
- `Secret scanning alerts: read`
- `Repository security advisories: read`
- optional `Members: read` fuer Ownership-/Assignee-/Team-Kontext
- optional `Organization Projects: read`, falls ein Modusmono-Board org-owned ist

Regel:

- Security-Read ist ein optionaler Erweiterungsblock
- Security-Read ist kein Anlass fuer Write-/Dismiss-/Admin-Rechte

## Was ausdruecklich nicht erlaubt ist

Das Snapshot-MVP darf nicht:

- `Contents: write` nutzen
- `Issues: write` nutzen
- `Pull requests: write` nutzen
- `Actions: write` nutzen
- `Checks: write` nutzen
- `Administration`-Rechte verlangen
- Secrets lesen oder schreiben
- Dependabot-Secrets lesen oder schreiben
- Repo-Settings aendern
- Workflows dispatchen, rerunnen, approven oder canceln
- Reviews schreiben, dismissen oder submitten
- Issues/PRs automatisch erstellen, kommentieren, labeln oder schliessen

Kurz:

- Snapshot ist read-only.
- Snapshot ist keine Mutationserlaubnis.
- Write-Automation muss spaeter separat entschieden werden.

## Datenmodell fuer Snapshot Output

### Pflichtfelder

```json
{
  "repo": "jannekbuengener/Claire_de_Binare",
  "snapshot_time": "2026-06-30T00:00:00Z",
  "open_issues_summary": {},
  "open_prs_summary": {},
  "blocked_prs": [],
  "merge_ready_prs": [],
  "red_or_stale_checks": [],
  "failed_actions_runs": [],
  "relevant_actions_logs": [],
  "review_blockers": [],
  "labels_missing_or_inconsistent": [],
  "project_v2_reconciliation": {},
  "rate_limit_status": {},
  "api_limitations": [],
  "recommended_next_actions": []
}
```

### Empfohlene Zusatzfelder

```json
{
  "auth_profile": {
    "mode": "gh-session | fine-grained-pat | classic-pat | github-app",
    "project_read_available": true,
    "checks_read_available": true
  },
  "evidence_sources": [],
  "partial_visibility": [],
  "collection_errors": []
}
```

### Modellierungsregeln

- unvollstaendige Sicht muss als unvollstaendige Sicht markiert werden
- fehlende ProjectV2-Leserechte duerfen nicht stillschweigend als "kein Drift"
  interpretiert werden
- fehlende Checks-Sicht duerfen nicht stillschweigend als "alles gruen"
  interpretiert werden

## Beispiel-Snapshot

```json
{
  "repo": "jannekbuengener/Claire_de_Binare",
  "snapshot_time": "2026-06-30T00:12:00Z",
  "open_issues_summary": {
    "total_open": 42,
    "high_signal": [1445, 3362, 3384, 3345],
    "possible_duplicates": []
  },
  "open_prs_summary": {
    "total_open": 5,
    "drafts": 0,
    "clean_merge_state": [3532, 3530, 3529, 3528, 3527]
  },
  "blocked_prs": [],
  "merge_ready_prs": [3532, 3530, 3529, 3528, 3527],
  "red_or_stale_checks": [],
  "failed_actions_runs": [],
  "relevant_actions_logs": [],
  "review_blockers": [],
  "labels_missing_or_inconsistent": [],
  "project_v2_reconciliation": {
    "status": "unknown_partial_visibility",
    "reason": "read:project missing in current auth profile"
  },
  "rate_limit_status": {
    "rest": "check headers or /rate_limit",
    "graphql": "check GraphQL cost and remaining budget"
  },
  "api_limitations": [
    "ProjectV2 not fully visible without project read",
    "fine-grained PAT cannot be treated as universal for Checks + user-owned Projects"
  ],
  "recommended_next_actions": [
    "If ProjectV2 is required, use an auth profile with project read",
    "If broad repeatable portfolio snapshots are needed, evaluate a GitHub App"
  ]
}
```

## Agenten-Workflow

### Phase 0: Auth und Sicht pruefen

- `gh auth status`
- Repo identifizieren
- sichtbare Faehigkeiten pruefen
- ProjectV2-Read pruefen
- bei fehlender Sicht `partial_visibility` setzen

### Phase 1: Basis-Snapshot sammeln

- Repo-Metadaten
- offene Issues
- offene PRs
- Reviews / Review-Blocker
- Check-/Status-Sicht
- Actions-Runs / Jobs / Logs-Referenzen
- Label-Konsistenz
- ProjectV2-Reconciliation
- Rate-Limit-Status

### Phase 2: Normalisieren

- Blocker aus PRs/Reviews/Checks ableiten
- merge-ready PRs separat ausweisen
- rote oder stale Checks separat ausweisen
- Follow-up-Empfehlungen erzeugen

### Phase 3: Ausgabe erzeugen

- JSON fuer Maschinenkonsum
- Markdown fuer Menschenkonsum
- keine Live-Mutation

### CLI-MVP-Richtung

- `gh api graphql --input <query-file>`
- `gh api repos/{owner}/{repo}/actions/runs`
- `gh api repos/{owner}/{repo}/commits/{ref}/status`
- `gh api repos/{owner}/{repo}/issues`
- `gh api repos/{owner}/{repo}/pulls`
- `gh api repos/{owner}/{repo}/labels`

## Rate-Limit- und Best-Practice-Regeln

### Primary Limits

- unauthenticated REST: `60/h`
- authenticated user REST: `5000/h`
- `GITHUB_TOKEN` in Actions: `1000/h` pro Repo
- GitHub App installations: mindestens `5000/h`, je nach Kontext auch hoeher

### Secondary Limits

Wichtige Grenzen laut GitHub:

- max `100` gleichzeitige Requests
- REST typischerweise `900` Punkte pro Minute
- GraphQL typischerweise `2000` Punkte pro Minute
- Content-generierende Requests haben eigene harte Limits

### Snapshot-Best-Practices

- GraphQL nutzen, um Mehrfachabfragen zu reduzieren
- Pagination sauber implementieren
- Rate-Limit-Header aus Responses lesen
- `GET /rate_limit` sparsam verwenden
- bei `403`/`429` Backoff respektieren
- Logs nur bei relevanten Fehlruns ziehen
- Project-/Security-Teile nur sammeln, wenn das Auth-Profil sie wirklich sehen darf
- Output muss `partial_visibility` und `api_limitations` ausweisen

## Risiken / Grenzen

### Auth-Limitierungen

- fehlendes `read:project` blendet ProjectV2 aus
- fine-grained PAT deckt nicht alle benoetigten Flächen vollstaendig ab
- user-owned Projects sind mit fine-grained PAT laut GitHub eingeschraenkt
- Checks API ist mit fine-grained PAT laut GitHub eingeschraenkt

### Produktgrenzen

- Snapshot ist nur so gut wie die sichtbare API-Flaeche
- ProjectV2, Checks und Security koennen auth-abhaengig teilweise sichtbar sein
- Logs sind oft teuer und nur selektiv sinnvoll

### Governance-Grenzen

- Snapshot ist keine Freigabe
- Snapshot ist keine Merge-Erlaubnis
- Snapshot ist keine LR-/Live-/Echtgeld-Aussage

## MVP-Plan

### Phase 0: Docs only

- Capability-Map und Permission-Profil dokumentieren
- keine Tokens erzeugen
- keine Repo-Settings aendern
- keine Runtime aendern

### Phase 1: CLI-MVP

- read-only Snapshot fuer ein Repo
- `gh api` + GraphQL Query-Dateien
- Markdown + JSON Output

### Phase 2: Modusmono-Portfolio

- Multi-Repo-Snapshot fuer CDB und weitere Repos
- org-/portfolio-weite ProjectV2-Reconciliation

### Phase 3: Agent Integration

- Snapshot als Standard-Preflight fuer CDB-/Modusmono-Agenten
- `API Opportunity`-Hinweis bei wiederkehrender manueller GitHub-Arbeit

### Phase 4: GitHub App Zielbild

- App-basierte Read-Architektur statt user-gebundener Dauerloesungen evaluieren
- Permissions minimal, aber breit read-only halten

## Follow-up-Issues

- `[GITHUB-API][MVP] Build read-only Unified GitHub Status Snapshot CLI`
- `[GITHUB-API][GRAPHQL] Add reusable ProjectV2/statusCheckRollup query bundle`
- `[GITHUB-API][AGENTS] Add API Opportunity Scan to CDB/Modusmono agent prompts`
- `[GITHUB-API][APP] Evaluate GitHub App target architecture`

## Official GitHub Docs Researched

- REST overview:
  `https://docs.github.com/en/rest/about-the-rest-api/about-the-rest-api`
- GraphQL overview:
  `https://docs.github.com/en/graphql`
- `gh api` manual:
  `https://cli.github.com/manual/gh_api`
- REST rate limits:
  `https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api`
- `GITHUB_TOKEN` permissions:
  `https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication`
- PATs and limitations:
  `https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token`
- GitHub App permissions:
  `https://docs.github.com/en/apps/creating-github-apps/setting-up-a-github-app/choosing-permissions-for-a-github-app`
- Issues REST:
  `https://docs.github.com/en/rest/issues/issues`
- Pull Requests REST:
  `https://docs.github.com/en/rest/pulls/pulls`
- Pull Request Reviews REST:
  `https://docs.github.com/en/rest/pulls/reviews`
- Labels REST:
  `https://docs.github.com/en/rest/issues/labels`
- Commit Statuses REST:
  `https://docs.github.com/en/rest/commits/statuses`
- Contents REST:
  `https://docs.github.com/en/rest/repos/contents`
- Actions workflow runs REST:
  `https://docs.github.com/en/rest/actions/workflow-runs`
- Checks REST overview:
  `https://docs.github.com/en/rest/checks`
- Fine-grained PAT permissions matrix:
  `https://docs.github.com/en/rest/overview/permissions-required-for-fine-grained-personal-access-tokens`

## Schlussfolgerung

Fuer das Snapshot-MVP ist die richtige Sicherheitsstrategie nicht ein extrem eng
geschrumpfter Read-Scope, sondern ein ehrliches breites Read-only-Profil mit
klaren Sichtbarkeitsgrenzen. Broad read, narrow write ist hier die saubere
Linie.
