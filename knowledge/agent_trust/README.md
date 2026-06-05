# Agent Trust – Audit & Scoring

Auditierbarer Trust-Ledger und Score-Snapshots für Agenten (Claude, Codex, Gemini, Copilot, OpenCode, …).

**Regel:** `ledger/` ist append-only. Korrekturen über neue Events, nicht Edit.

## Key entrypoints
*   [Trust score policy (knowledge/governance/CDB_TRUST_SCORE_POLICY.md)](../governance/CDB_TRUST_SCORE_POLICY.md)
*   [Config (knowledge/governance/TRUST_SCORE_CONFIG.yaml)](../governance/TRUST_SCORE_CONFIG.yaml)
*   [Policy cards (knowledge/governance/policy_cards/)](../governance/policy_cards/)
*   [Ledger (ledger/)](ledger/) · [Snapshots (snapshots/)](snapshots/) · [Incidents (incidents/)](incidents/)

## SSOT boundary
Trust scores inform governance; they do **not** authorize live trading. LR **NO-GO**.
