# Evidence: cdb-secrets-rotator Sample Outputs

This directory contains **sample outputs** from `Rotate-Secrets.ps1` to demonstrate:
- Safe logging (no secret values)
- Idempotency (repeated operations)
- Fail-closed validation
- Two-step workflow (plan → apply → export)

## Files

| File | Description |
|------|-------------|
| `sample_plan_output.md` | Output from `plan` command (dry-run) |
| `sample_apply_output.md` | Output from `apply` command (rotation) |
| `sample_export_output.md` | Output from `export` command (.env.runtime generation) |

## Purpose

These outputs serve as:
1. **Documentation:** Show expected tool behavior
2. **Acceptance Criteria:** Verify guardrails work as designed
3. **Audit Trail:** Demonstrate safe logging (no values exposed)
4. **Reference:** Help users understand tool output format

## Safety

All sample outputs:
- ✅ Show secret **names** (safe)
- ✅ Show secret **lengths** (safe)
- ✅ Show **actions** (CREATE/UPDATE/SKIP)
- ❌ Never show secret **values**
- ❌ Never show secret **hashes** (could leak entropy)

## Usage

These are **examples only** - your actual outputs will vary based on:
- Secrets already present in `$SECRETS_PATH`
- First run vs. subsequent runs (idempotency)
- Manifest changes (added/removed secrets)

---

**Generated:** 2026-01-28
**Tool Version:** v1.0
