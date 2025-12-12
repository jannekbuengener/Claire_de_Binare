# CDB_AGENT_POLICY
**KI-/Agenten-Regeln (Mini-Stack)**  
Version: 1.0.0 • Date: 2025-12-12 • Status: Canonical

---

## 1. Ziel
Regelt, wie KI-Modelle und Agent-Rollen im Projekt arbeiten dürfen, ohne:
- Blackbox-Risiko
- Tresor-Verletzung
- Repo-Chaos
- Vendor-Lock-In

---

## 2. Rollenlogik
- „Agent“ = Rolle/Scope, keine autonome Entität.
- Session Lead orchestriert; Peer-Modelle liefern Inputs.

### Beispielrollen
- system-architect
- risk-guardian
- infra-advisor
- rl-safety-officer

---

## 3. Write-Gates (hart)
KI darf persistent schreiben **nur** in:
- `CDB_KNOWLEDGE_HUB.md` (kanonischer KI-Speicher im Repo)
- `.cdb_agent_workspace/*` (lokal, gitignored, Scratch)

KI darf **nicht** persistent schreiben in:
- `/core`, `/services`, `/infrastructure`, `/tests`
- `/governance/*`
- irgendetwas in der Tresor-Zone

### Technical Enforcement (REQUIRED)
- Branch Protection: PR-only Workflow fuer main/master und geschuetzte Pfade; keine Direct Pushes, keine Force-Pushes/BYPASS (auch nicht fuer Admins).
- Non-Bypass: Merge ist technisch nur moeglich, wenn alle Required Status Checks (Tests, Lint, Write-Zonen-Check, Secrets-Scan, Conversation Resolution) gruen sind.
- CODEOWNERS: Pflicht-Reviewer fuer /core, /governance, /infrastructure, /tests (mind. Maintainer-Team).
- Write-Zonen-Validierung: CI-Skript `scripts/validate_write_zones.sh` blockt PRs mit Verstoessen; pre-commit Hook prueft Pfade lokal.
- Audit: Abweichungen werden im PR kommentiert und im Repo-Log dokumentiert.

---

## 4. Verbotene Aktionen (nicht verhandelbar)
KI/Agents dürfen niemals:
- Secrets/Keys/Custody anfassen oder rekonstruieren
- Withdrawals/Capital-Moves auslösen
- Hard Limits ändern
- Kill-Switch/Safety umgehen oder modifizieren
- neue Top-Level-Strukturen im Repo anlegen
- „silent“ Änderungen durchführen (ohne PR/Review)

### Automated Secrets Detection (REQUIRED)
- Pre-commit: git-secrets oder gitleaks MUSS installiert und enforced sein.
- CI: truffleHog/detect-secrets scannt PR-Diffs; custom Regex für projektspezifische Tokens; Block on detection.
- Non-Bypass: Merge ohne erfolgreichen Secrets-Scan ist technisch unmöglich; keine Direct Pushes/Force-Pushes mit Secrets.
- False Positives: `.secretsignore` pflegen; Incident Playbook für Rotation + Audit + PR-Hinweis anwenden.

---

## 5. Analysis vs Delivery
- Analysis: Vorschläge/Pläne/Checks, keine Repo-Mutation.
- Delivery: nur nach User-Go, nur als Diffs/PRs, mit Tests + Rollback.

### PR Workflow Enforcement (REQUIRED)
- Branch Protection: main/master MUSS PR-basiert sein; keine Direct Pushes/Force-Pushes/BYPASS (auch nicht fuer Admins); stale Reviews werden verworfen.
- Reviews: mind. 1 Approval; fuer /governance und /core mind. 2.
- Required Checks: Tests gruen, Lint, Write-Zonen-Check, Secrets-Scan, Conversations resolved; Merge ohne alle Checks ist technisch unmoeglich.
- PR-Template: Rollback-Plan ist Pflicht; Hotfixes laufen ebenfalls als PR.

---

## 6. Dev-Freeze (KI-Ausfall)
Bei Ausfall vertrauenswürdiger Coding-KI:
- keine Änderungen an Code/Infra/Policies
- Betrieb erlaubt, Mutation verboten
- Status im Knowledge Hub dokumentieren

### Technical Enforcement (REQUIRED)
- Freeze-State: Datei `.dev_freeze_status` im Repo; CI bricht Merge ab, falls aktiv.
- PR-Kommentar: Action kommentiert offene PRs, wenn Freeze aktiv ist.
- Notification: Slack/Email Alert bei Aktivierung; Ownership klar benennen.
- Unfreeze: mind. 2 Maintainer Approval + dokumentierter Commit; Post-Freeze Audit fuer aufgelaufene Changes.

---

## 7. Open-Source / Unabhängigkeit
- Keine KI-spezifischen Hardcodings in Runtime/Infra.
- KI ist austauschbares Tooling; Kernsystem bleibt OSS-fähig und lauffähig.
