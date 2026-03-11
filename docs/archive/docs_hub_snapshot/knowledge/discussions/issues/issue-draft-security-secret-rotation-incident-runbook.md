# Secret Rotation & Incident Runbook

Status: CLAUDE_READY
Mode: EXECUTION_ONLY
Labels: [security, secrets, docs, devops]
Milestone: Security / M8

Goal:
Operationalize secret rotation and incident response with a clear, actionable runbook that is tied to owners, cadence, and verification steps. It must be concise and executable during outages.

Non-Goals:
- Performing live rotations or revocations in this issue.
- Procuring external incident response services.
- Writing broad security policy unrelated to secret handling.
- Changing CI/CD pipelines beyond documenting expectations.
- Defining new secret storage mechanisms or providers.

Files/Paths to touch:
- SECURITY_ISSUES.md
- Claire_de_Binare_Docs/docs/content/security/secret-rotation-runbook.md
- Claire_de_Binare_Docs/docs/content/security/incident-response-secrets.md
- Claire_de_Binare_Docs/data/secret-rotation-matrix.yaml

Ordered Steps:
1. Define secret classes (database, cache, API keys, monitoring) and map each to a rotation owner and cadence.
2. Write a rotation runbook with exact steps, pre-checks, rotation steps, and validation checks.
3. Write an incident response playbook for suspected leakage, including containment, revocation, and comms.
4. Add a post-incident verification checklist to confirm services and CI are stable after rotation.
5. Document required approvals and escalation paths for emergency rotations.
6. Create a machine-readable rotation matrix that lists owners, cadence, and last-rotated fields (no values).
7. Link the runbook and incident playbook from SECURITY_ISSUES.md so it is discoverable.
8. Add a lightweight quarterly review reminder to keep the runbook current.

Acceptance Criteria:
- Rotation runbook exists in the Docs Hub and covers all secret classes in use.
- Incident response playbook exists with clear containment and communication steps.
- A rotation matrix file exists with owner, cadence, and scope for each secret class.
- SECURITY_ISSUES.md references both runbook and incident response documents.
- Procedures include verification steps that confirm services recover after rotation.
- No secret values or sensitive identifiers are stored in the docs or matrix.
- The runbook includes an explicit rollback plan for failed rotations.
- Runbook includes owner/contact fields and links back to the secret inventory.

Risks:
- Incomplete ownership mapping could stall incident response.
- Overly generic steps may not be actionable during real incidents.
- Drift between documented cadence and actual rotations over time.
- Rotation may cause service downtime if validation steps are weak.
- Runbook may become stale as owners, services, or secret names change.

Rollback:
- Revert the new runbook and matrix files if they are incorrect.
- Remove references from SECURITY_ISSUES.md if they point to obsolete guidance.
- Restore the prior operational process if documented steps are unworkable.
