# Parameter Control Policy Register v1

Machine-readable control register for Claire de Binare parameter and control
surfaces. This folder is **documentation and governance evidence only**.

It does **not** authorize:

- automatic runtime / paper / live configuration generation
- threshold tuning or optimization campaigns
- productive DB or MCP mutation
- Live / Echtgeld Go

Existence in the register is not an optimization permit.

## Files

| File | Role |
|------|------|
| `CDB_PARAMETER_CONTROL_POLICY.json` | **Canonical** register body |
| `CDB_PARAMETER_CONTROL_POLICY.schema.json` | JSON Schema (`register.v1`) |
| `CDB_PARAMETER_CONTROL_POLICY.yaml` | Discovery / metadata pointer only (no rule-body duplicate) |
| `README.md` | This document |

## Schema resolution

`schema_version`: `cdb.parameter_control_policy.register.v1`

Each rule is an object with the 19 register dimensions required by Issue #4148:

1. `parameter_id`
2. `exact_name`
3. `aliases`
4. `system_area`
5. `owner`
6. `repository_paths`
7. `consumers`
8. `effective_default`
9. `override_precedence`
10. `unit`
11. `allowed_range`
12. `main_class`
13. `technical_adjustability`
14. `change_authority`
15. `context_validity`
16. `safety_classification`
17. `snapshot_and_provenance_requirement`
18. `test_and_evidence_requirement`
19. `lifecycle_status`

Optional `analysis` holds historical extract notes, compact-decision mapping, and
path/name drift evidence. It is not a substitute for the 19 dimensions.

### Enums

`change_authority`:

- `RESEARCH_ALLOWED`
- `CONDITIONAL_AFTER_EVIDENCE`
- `FROZEN_UNTIL_CONTRACT`
- `GOVERNANCE_ONLY`
- `MUST_NOT_OPTIMIZE`
- `FORBIDDEN`

`lifecycle_status`:

- `active` | `implicit` | `duplicated` | `dead` | `documented-only` | `invariant`

`context_validity` uses full context names (`replay`, `paper`, `runtime`, `live`,
`docs`, `tests`) plus optional compact codes.

## Owner convention

`owner` is a **repo-backed technical service or domain owner**, for example:

- `service:signal`
- `service:risk`
- `domain:governance`
- `domain:ci`

Never invent a person. Every owner must cite derivation evidence (path,
SERVICE_CATALOG mapping, or governance surface). If that evidence is missing,
use a structured unresolved object.

## Evidence rules

- Values originate from the historical analysis at
  `main@224cfd49398b329b315781372658fab1fbf15362` and the register extract.
- Every path is re-verified against current `origin/main`.
- Stale or label-only paths are remapped in `path_remediation` (no silent drops).
- Do not invent defaults, owners, units, or ranges.
- `unit` / `allowed_range` may be `not_applicable` with reason.
- Unresolved fields use:

```json
{
  "resolution_status": "unresolved",
  "reason": "...",
  "required_follow_up": true
}
```

`status` may become `canonical` only when validators/tests are green and
`unresolved_count = 0`.

## Research vs MUST_NOT_OPTIMIZE

- Research / replay surfaces may be `RESEARCH_ALLOWED` or
  `CONDITIONAL_AFTER_EVIDENCE` under explicit issue scope and evidence.
- Risk, kill-switch, live gates, secrets, Stage-A/B, OOS, stress, LR, and hard
  invariants remain `MUST_NOT_OPTIMIZE`, `GOVERNANCE_ONLY`, or `FORBIDDEN`.
- Listing a parameter in this register never lifts those freezes.

## Fingerprints

Two distinct hashes are required:

1. **`register_fingerprint` (JSON)**
   SHA-256 of the deterministically normalized `rules` array only:
   - `json.dumps(rules, ensure_ascii=False, sort_keys=True, separators=(',', ':'))`
   - UTF-8 encode → SHA-256 hex
   The `register_fingerprint` field itself is **excluded** from the hashed body.

2. **`canonical_json_sha256` (YAML pointer)**
   SHA-256 of the **full** canonical JSON file bytes on disk.

The validator recomputes both and fails on drift.

## Maintenance

1. Edit the canonical JSON (keep `parameter_id` stable; sort by `parameter_id`).
2. Recompute fingerprints via `python -m tools.validate_parameter_control_policy`
   (or update YAML hashes after a passing validator run that prints them).
3. Keep YAML as pointer-only metadata.
4. Do not commit external SourceDocs (DOCX / extract).
5. Run:

```powershell
python -m json.tool config/parameter-control/v1/CDB_PARAMETER_CONTROL_POLICY.json > $null
python -m json.tool config/parameter-control/v1/CDB_PARAMETER_CONTROL_POLICY.schema.json > $null
python -m tools.validate_parameter_control_policy
pytest -q tests/unit/governance/test_parameter_control_policy.py
```

## Safety posture

Default-deny. Unknown parameter, missing evidence, and live context are denied.
Stage-A/B, OOS, stress, risk, and live boundaries stay frozen unless a separate
canonical governance decision supersedes this document.

No ML / RL roadmap, dependency, or optimization surface may be introduced here.

Refs: #4147, #4148, PR #4154.
