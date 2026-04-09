# CDB Control Follow-up Classifier

Zweck: Duenne Human-in-the-loop Operationalisierung fuer repo-backed Control-Findings.

## Scope

- nutzt `.github/prompts/cdb-control-followup.prompt.yml`
- laeuft nur manuell ueber `.github/workflows/cdb-control-followup-classifier.yml`
- klassifiziert nur in:
  - `report_only`
  - `follow_up_issue`
  - `unclear`
- erstellt keine Issues automatisch
- mutiert das Repo nicht aus dem Modellresultat heraus

## Ausfuehrung

1. GitHub Actions -> `CDB Control Follow-up Classifier`
2. `finding_text` mit einem konkreten repo-backed Finding fuellen
3. optional `issue_number` setzen, wenn das Ergebnis auch als Kommentar auf ein bestehendes Issue soll
4. `output_target`:
   - `summary_only`
   - `summary_and_issue_comment`

## Ergebnis

- Step Summary zeigt Finding und validiertes JSON-Ergebnis
- Artefakt `cdb-control-followup-classification` enthaelt:
  - `result.json`
  - `summary.md`
- optional wird dieselbe Summary als Kommentar an das gesetzte Issue geschrieben

## Guardrails

- fail-closed bei ungueltigem JSON
- fail-closed bei nicht numerischer `issue_number`
- `follow_up_issue` nur bei kleinem, getrennt bearbeitbarem Fixpaket
