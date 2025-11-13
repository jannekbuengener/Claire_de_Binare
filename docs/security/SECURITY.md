# SECURITY

## Runtime-Policies
- Container-Services laufen als non-root (UID ≠ 0); Verstöße sind als Security-Finding zu behandeln.
- `cap_drop: ["ALL"]` und `security_opt: ["no-new-privileges:true"]` sind verpflichtend; Abweichungen werden unter `backoffice/artifacts/<RUN_DATE>/security/runtime_security_check.txt` dokumentiert.
- Trivy wird ohne `--ignore-unfixed` ausgeführt, außer eine gepflegte `.trivyignore` liegt vor **und** die Ausnahme ist im `backoffice/docs/DECISION_LOG.md` dokumentiert (Owner, Ablaufdatum, Risk-Akzeptanz).
- Offene Ports werden best effort mit plattformabhängigem Tool (Linux: `ss` → `lsof` → `netstat`, macOS: `lsof`, Windows: `netstat`) und hartem Timeout von ≤10 s erfasst; fällt der Schritt aus, wird ein Hinweis in `open_ports.txt` vermerkt.

## Re-Run / Evidence-Policy
- **Re-Run Pflicht:** Security-Ergebnisse sind nur gültig, wenn der Re-Run gemäß `backoffice/docs/TEST_RUNBOOK.md` durchgeführt wurde.
- **Scope:** Bandit, Gitleaks (mit `--redact`), Trivy (vuln/secret/config), Offene Ports (`ss -tulpen`), Docker-Runtime-Inspection (`docker inspect`).
- **Artefakte:** `backoffice/artifacts/<RUN_DATE>/security/`.
- **Evidence:** Abschnitt „Security“ in `TEST_RERUN_EVIDENCE_<RUN_DATE>.md` muss `✅` enthalten.
- **Deviation-Handling:** Findings werden im Evidence-Dokument unter „Abweichungen“ tabellarisch geführt und per Issue verlinkt.
