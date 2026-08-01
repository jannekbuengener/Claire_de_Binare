---
relations:
  role: contract
  domain: agents
  upstream:
    - knowledge/governance/CDB_CONSTITUTION.md
    - knowledge/governance/CDB_AGENT_POLICY.md
    - knowledge/governance/CDB_AGENT_CONTROL_PLANE.md
    - docs/runbooks/PR_ROUTING_AND_BATCH_MERGE_POLICY.md
    - tools/pr_routing/
  downstream:
    - tools/agent_execution_contract/
    - docs/contracts/cdb_agent_execution.v1.schema.json
  status: technical_contract
  tags: [agents, control-plane, execution-contract, router-handoff]
---

# CDB Agent Execution Contract v1

Status: Technical contract (schema/tooling)
Schema id: `cdb.agent_execution.v1`
Schema version: `1.0.0` (fixtures) / `1.1.0` (optional `provider_work_order`)
Issue: `#4251` (base) / `#4254` (work-order binding)
Parent: `#4249`
Predecessor canon: `#4250` /
`knowledge/governance/CDB_AGENT_CONTROL_PLANE.md`
(Owner-ratified 2026-08-01 at `c691a8d0`)

Authority boundary: This contract does **not** amend Constitution, Governance,
or `CDB_*_POLICY.md`. Permissions it encodes remain subordinate to binding
governance and the ratified ACP Truth Order.

## 1. Zweck

`cdb.agent_execution.v1` ist die provider-neutrale, maschinenlesbare Übergabe
vom **read-only PR Router** an spätere Dispatcher und Provider. Der Contract
beschreibt maximale Autorität für einen Delivery-Lauf. Er startet keinen Lauf
und autorisiert keinen Merge.

Geplante Konsumform (nicht in diesem Slice implementiert):

```text
dispatch --contract <PATH>
```

## 2. Offizielle Quellen vs. CDB-Entscheidungen

| Aussage | Quelle |
| --- | --- |
| Schema-Dialekt Draft 2020-12 (`$schema`, `additionalProperties`, `const`) | [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12) |
| Deterministische JSON-Serialisierung vor Hash | [RFC 8785 JSON Canonicalization Scheme](https://www.rfc-editor.org/info/rfc8785/) |
| SHA-256 Digest-Encoding `sha256:<lowercase-hex>` | CDB contract convention (bestehende `docs/contracts/*`) |
| Permission-/Attenuation-/Delivery≠Merge-Modell | Binding policies + PR-Routing runbook + ratified ACP `#4250` + dieses Contract |
| Cursor Cloud Agents API Felder (`env`, `repos`, `prompt`) | [Cursor Cloud Agents API](https://cursor.com/docs/cloud-agent/api/endpoints) — nur Provider-Handoff-Abgleich; **keine** Kernschema-Autorität |

## 3. Identity und Versionierung

Pflichtfelder: `schema_id`, `schema_version`, `contract_id`, `created_at`,
`producer`, `issue`, `route`, `integrity`.

- `schema_id` ist exakt `cdb.agent_execution.v1`.
- `schema_version` ist `1.0.0` oder additiv `1.1.0`.
- Optional ab `1.1.0`: `provider_work_order` mit `prompt_ref`, `source_commit`,
  `prompt_digest` (`sha256:<hex>`). Bestehende `1.0.0`-Fixtures ohne Work Order
  bleiben gültig. Live-Cursor-Dispatch verlangt die Bindung (#4254).
- Unknown fields werden fail-closed abgelehnt (`additionalProperties: false`).
- Breaking Änderungen erfordern `cdb.agent_execution.v2` (neues Schema),
  nicht stille Erweiterung von v1.

## 4. Permissions

Alle Boolean-Permissions sind Pflichtfelder. Fehlende Felder sind ungültig und
dürfen niemals als `true` interpretiert werden. Sichere Defaults im Handoff-
Adapter starten bei `false` außer explizit gesetztem `read_repo`.

Pflichtflags:

`read_repo`, `write_code`, `write_docs`, `commit`, `push`, `open_pr`,
`update_pr`, `comment_issue`, `close_issue`, `publish_cdb_local_ci`, `merge`,
`runtime_mutation`, `database_mutation`, `mcp_live_mutation`.

Regeln:

- Provider dürfen Rechte nur reduzieren (`true→false`).
- `false→true` ist `CONTRACT_PERMISSION_ESCALATION`.
- Approval oder erfolgreiche Targeted Tests erhöhen keine Rechte.
- Normale Delivery-Contracts haben `merge=false` und
  `publish_cdb_local_ci=false`.
- `merge_authority.granted` ist für Delivery-Agent/Provider immer `false`.

## 5. Execution Scope

Pflicht: `allowed_paths`, `forbidden_paths`,
`allowed_commands_or_command_classes`, `issue_scope`, `delivery_target`,
`stop_conditions`.

- Leere/fehlende Allowlist bedeutet keine Schreibberechtigung.
- Forbidden schlägt Allowed (semantische Auswertungsregel für Consumer).
- Pfade sind repo-relativ; Traversal/Alias-Umgehungen werden abgelehnt.

## 6. Budget und Environment

Budgetpflicht: `wall_time_seconds`, `max_iterations`, `max_tool_calls`,
`network_policy` — nur endliche nichtnegative Integer; kein implizites
Unendlich.

Environmentpflicht: `environment_profile`, `provider_profile`, `mcp_profiles`,
`skills`, `subagents`, `secret_references`.

- Kernschema bleibt provider-neutral.
- Cursor-spezifische Werte nur unter `environment.provider_profile.extensions`
  (z. B. API-Felder `env.type`, `repos`, `workOnCurrentBranch` als Referenz —
  nicht als Kernpflicht).
- Secrets ausschließlich als Referenz (`env:NAME`, `secret:NAME`, `file:PATH`).
- Keine Secret-Werte in Contract, Logs, Fixtures oder Evidence.

## 7. Validation und Delivery

Pflicht: `required_validations`, `evidence_requirements`,
`allowed_delivery_statuses`, `merge_authority`.

Grenzen (ACP Canon):

- Targeted Slice Validation ≠ Final-Head-CI / `cdb-local-ci`.
- Agent Run Evidence ≠ Final-CI Evidence.
- Delivery und Merge bleiben getrennte Vorgänge.

## 8. Serialisierung und Integrity

1. Hash-Input = Contract-Objekt **ohne** Feld `integrity.digest`.
2. Canonicalisierung = RFC 8785 JCS (UTF-8, sortierte Keys, kein Whitespace).
3. Zahlen: nur finite Integer; `NaN`/`Infinity`/Float werden abgelehnt.
4. Digest = `sha256:` + lowercase hex über die UTF-8-Bytes der kanonischen Form.
5. Semantisch identische Contracts mit anderer Key-Reihenfolge/Whitespace teilen
   denselben Digest; jede autoritätsrelevante Wertänderung ändert den Digest.
6. Keine stille Fallback-Serialisierung.

Tooling: `python -m tools.agent_execution_contract validate|digest|canonicalize|seal|handoff|attenuate`.

## 9. Provider Attenuation

Der Basiscontract ist die maximale Autorität. Provider-Overrides dürfen:

- Permissions nur `true→false` setzen,
- Scope/Budget/Netzwerk nur weiter einschränken,
- Stop-Conditions nicht entfernen,
- Kernfelder nicht überschreiben.

CLI: `python -m tools.agent_execution_contract attenuate --contract ... --override ...`.

## 10. Router-Handoff

- PR Router bleibt read-only und trifft keine Mergeentscheidung.
- Contract-Erzeugung erfolgt deterministisch aus validierter Router-Ausgabe und
  **expliziter Policy** (`tools/agent_execution_contract/handoff.py`).
- Kein Contract darf allein aus untrusted Issue-Text Rechte ableiten.
- Direkte Einbettung in `tools/pr_routing` ist absichtlich nicht Teil dieses
  Slices (Restgrenze): Adapter + Spec sind die technische Integrationsgrenze;
  Dispatcher folgt in `#4253`.

Beispiel:

```bash
python -m tools.agent_execution_contract handoff \
  --router-result route.json \
  --policy policy.json \
  --agent cursor-cloud \
  --created-at 2026-08-01T20:00:00Z \
  --output contract.json
```

## 11. Fixtures und Tests

Positive/negative Fixtures unter
`docs/contracts/examples/agent_execution/`.
Unit-Tests unter `tests/unit/governance/test_agent_execution_contract_v1.py`.

## 12. Nicht-Ziele

- Kein Live-Dispatch, kein Registry/Reconciler (`#4252`), kein Dispatcher
  (`#4253`), kein Cursor Provider Adapter (`#4254`), kein Environment-
  Provisioning (`#4255`), kein Run-Evidence-System (`#4256`).
- Kein Merge, kein `cdb-local-ci` Publish, kein Issue-Close durch diesen Contract.
- LR bleibt **NO-GO**.
