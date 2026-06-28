# Decision: ACCOUNT_BLOCKED_CHECK_WAIVER Evaluation for PR #3129

**Status:** DECISION_EXECUTED (historical record)
**Erstellt:** 2026-06-12
**Auftrag:** CI/GOV — Define handling for billing/account-blocked required checks
**Anmerkung:** PR #3129 wurde am 2026-06-12 gemergt. Der empfohlene HOLD-bis-Billing-Fix-Pfad (Option A) wurde wirksam umgesetzt. Dieses Dokument dient als historischer Governance-Nachweis.

---

## Live-Lage

| Surface | Status |
|---------|--------|
| PR #3129 | OPEN, kein Draft, mergeable (keine Konflikte) |
| Basis | `main` |
| Head | `policy/3096-evidence-class-enforcement` |
| mergeStateStatus | UNSTABLE (durch nicht-required Checks) |
| reviewDecision | leer (kein Review-Block) |
| Billing-Account | LOCKED |

## Check-Befund

### Required Checks (Branch Protection `main`)

| Check | Status | Workflow |
|-------|--------|----------|
| `ci (Unit/Integration + Lint gesammelt)` | ✅ SUCCESS | `ci.yml` |
| `policy-gate` | ✅ SUCCESS | `Policy Gate` |

### Non-Required Checks (nicht in Branch Protection)

| Check | Status | Fehlergrund |
|-------|--------|-------------|
| `capture-intent` | ❌ FAILURE | "account is locked due to a billing issue" |
| `submit-pypi` | ❌ FAILURE | "account is locked due to a billing issue" |

**Befund:** Beide roten Checks sind **infra-blocked**, nicht code-failing. Sie starten nicht wegen Account-Lock. Identischer Fehlertext, kein Log-Inhalt.

### Conversation Resolution

Branch Protection hat `required_conversation_resolution=true`. Alle Review-Threads sind resolved (letzter Stand: alle vier P1/P2-Kommentare wurden per Commit und Reply adressiert).

## Governance-Bewertung

### Anker-Dokumente

- `docs/runbooks/merge_policy_ci_gate.md` § "Current Classification: submit-pypi" (Zeilen 61-67): **`submit-pypi` ist explizit als nicht-merge-relevant klassifiziert.** Fehler sind "advisory diagnosis signal first, not as merge-contract failure."
- Branch Protection `main` (live via `gh api`): einzige required contexts sind `ci` und `policy-gate`. Keine ruleset-basierte Erweiterung.
- `capture-intent` hat kein `.github/workflows/`-Datei — kommt aus externem GitHub-App-Workflow (Auto Milestone PR Intent).

### Klassifikation

| Entscheidungsfläche | Wert |
|---------------------|------|
| CI/Workflow-Reality | Required Checks grün, non-required infra-blocked |
| Merge-Contract | Erfüllt (beide required checks pass) |
| Billing-Block | Infrastruktur-Problem, kein Code- oder Gate-Problem |
| Governance-Relevanz | Keine bestehende Regel für billing-blocked Waiver |

## Option A: HOLD bis Billing-Fix

- **Beschreibung:** PR offen lassen, kein Merge, bis Account-Billing behoben ist und alle Checks (auch non-required) grün sind.
- **Vorteil:** Konservativ, kein Risiko der Gate-Verwässerung, kein Waiver nötig.
- **Nachteil:** Unbestimmte Wartezeit; PR #3129 blockiert, obwohl fachlich READY; Folgearbeiten (#3096 schließen, #3127 voranbringen) hängen.

## Option B: ACCOUNT_BLOCKED_CHECK_WAIVER mit Jannek-GO

- **Beschreibung:** Merge bei grünen required checks, mit dokumentiertem Waiver für die billing-blockierten non-required Checks. Der Waiver gilt **ausschließlich** für diesen konkreten infra-Block. Nach Billing-Fix werden die betroffenen Checks ohne Code-Änderung rerunnt.
- **Waiver-Bedingungen:**
  1. Jannek erteilt explizites GO (Slack/Issue-Kommentar/verbal).
  2. HOLD-Kommentar auf PR #3129 vor Merge durch Waiver-Text ersetzt.
  3. Merge via `gh pr merge 3129 --squash --delete-branch` (ohne `--auto`).
  4. Nach Billing-Fix: manuelles Rerun der zwei fehlgeschlagenen Workflows.
  5. Nach Rerun: Erfolg reicht zur Bestätigung, kein erneuter Merge nötig.
- **Risiko:** Wahrnehmung, dass rote Checks ignoriert werden dürfen. Mitigation: Waiver ist explizit auf billing-blocked non-required Checks beschränkt; required Checks bleiben unverändert.

## Empfehlung

**Option A (HOLD)**. Begründung:

1. Kein operativer Druck für Sofort-Merge — PR #3129 ist evidenz-basierte policy-Arbeit, kein Hotfix.
2. Der Account-Billing-Lock sollte priorisiert behoben werden (ist ein separates Problem, das auch andere PRs/Workflows blockiert).
3. Nach Billing-Fix sind nur zwei Reruns nötig — kein zusätzlicher Code-Aufwand.
4. Ein Waiver für non-required Checks ist zwar governance-technisch vertretbar, erzeugt aber unnötiges narratives Risiko ("trotz roter Checks gemergt").

## Exakte Merge-Bedingungen (nach Billing-Fix)

1. Billing-Fix durch Account-Admin.
2. Rerun der beiden fehlgeschlagenen Workflows (capture-intent, submit-pypi) via `gh run rerun`.
3. **Alle vier Checks** müssen grün sein (ci, policy-gate, capture-intent, submit-pypi).
4. Merge via `gh pr merge 3129 --squash --delete-branch` (kein `--auto`).
5. Danach #3096 schließen.
6. Kein Product-Complete-Claim. #3087 bleibt CLOSED. LR bleibt NO-GO.

## Risiken

| Risiko | Eintritts-Wkeit | Mitigation |
|--------|-----------------|------------|
| Billing-Fix dauert >1 Woche | Mittel | Option B als Fallback nutzen |
| Nach Billing-Fix schlagen Checks doch fehl (Code-Problem) | Niedrig (billing war einzige Fehlerursache) | Code fixen, nicht Waiver nutzen |
| Non-Required Checks werden nachträglich required | Niedrig (müsste Branch Protection ändern) | Wachsamkeit bei Ruleset-Änderungen |

## Status

```
Status: DECISION_EXECUTED
Merged: PR #3129 am 2026-06-12 (Option A bestätigt)
Typ: Governance-Waiver-Evaluation (historisch)
Scope: PR #3129, billing-blocked non-required checks
Merge-allowed: false (damaliger Auftrag, inzwischen hinfällig)
LR: NO-GO (unverändert)
Product-Complete: kein Claim
#3087: CLOSED (bleibt geschlossen)
```
