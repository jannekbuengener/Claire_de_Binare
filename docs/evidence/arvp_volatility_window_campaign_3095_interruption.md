# ARVP Volatility-Window Campaign #1 — Interruption Record

**Campaign ID:** `arvp_3095_vol_window_20260608_2341`
**Document Class:** `interruption_record` (not `natural_paper_evidence`)

---

## Campaign Reference

| Field | Value |
|-------|-------|
| Campaign # | 1 of max 3 |
| Design issue | #3094 |
| Execution issue | #3095 |
| Existing evidence | `docs/evidence/arvp_volatility_window_campaign_3095.md` |
| PR | #3098 (merged at `7d20d677`, 2026-06-09T00:21:13Z) |

## Campaign Timeline

| Event | UTC | Source |
|-------|-----|--------|
| Campaign start | 2026-06-08T23:41:09Z | Evidence doc §Campaign Start |
| Last documented monitoring cycle (Cycle 4) | 2026-06-09T00:14:00Z | Evidence doc §Monitoring Cycles |
| Last valid evidence merged (PR #3098) | 2026-06-09T00:21:13Z | GitHub PR #3098 |
| Planned campaign end (max 8h) | ~2026-06-09T07:41:09Z | Policy §Per-campaign duration |
| Host shutdown (estimated) | ~2026-06-09T01:00–02:00 UTC (after 02:00 local) | Inference: host down before campaign end; no evidence between 00:14 and boot |
| Host reboot | 2026-06-09T10:00:20Z (12:00:20 local) | `Get-CimInstance Win32_OperatingSystem` |
| Reconciliation session | 2026-06-09T10:35:30Z | Current session |

## Interruption Classification

| Field | Value |
|-------|-------|
| **Status** | **HOLD_INTERRUPTED_BY_HOST_SHUTDOWN** |
| Interruption type | `host_shutdown` (local machine powered off / sleep / reboot) |
| Duration observed before interruption | ~34 min (4 monitoring cycles) |
| Events before interruption | **0** (DB-verified via `cdb_readonly` at 00:14 UTC) |
| Events during host-down period | **Unknown** (no DB access — Docker not running) |
| Campaign window completed? | **No** — host was down for the remaining ~7h of the 8h window |
| Docker available at reconciliation? | **No** — `docker ps` fails: daemon not running |
| DB query possible? | **No** — Postgres not reachable |

## Why No 8h Statement Is Possible

The campaign was designed as a max-8h observation window. At the time of host shutdown (~1–2h into the campaign), only ~34 min of observation had been documented. The remaining ~6–7h of the window occurred while the host was unavailable. It is impossible to determine:

- whether a SIGNAL fired during the host-down period
- whether a DECISION was produced
- whether a paper ORDER was placed or FILLED
- whether any `correlation_ledger` events were recorded
- whether regime state changed

The campaign therefore **cannot** be classified as:
- A completed 8h campaign (insufficient observation)
- A campaign failure (no evidence that no chain occurred — only that no observation was made)
- A successful campaign (no chain evidence)

## Why No Natural-Paper Evidence Was Produced

| Condition | Status | Detail |
|-----------|--------|--------|
| Chain produced (SIGNAL→DECISION→ORDER→FILL) | **Unknown** | No DB access; possible but unverifiable |
| `paper_reference_window.v1` extracted | **No** | No chain → no window to extract |
| `regime_segments` populated | **No** | No window → no scorecard possible |
| Evidence class `natural_paper_evidence` | **Not achieved** | Prerequisite: observable paper chain |

Even if a chain occurred during the host-down period, the evidence cannot be verified without DB access. This run does not produce verifiable `natural_paper_evidence`.

## Impact on #3087 — §5.2.4 Remains BLOCKED

| Gate | Status | Reason |
|------|--------|--------|
| §5.2.4 — at least one window with non-empty `regime_segments` | **BLOCKED** | Campaign #1 interrupted; no chain; unknown whether chain existed during downtime |
| Campaign #1 counted toward max-3 limit | **No** | Interrupted campaigns do not count as full campaign attempts per policy interpretation |
| Campaign #2 eligible | **Yes** | No campaign slots consumed; 24h min observation not yet relevant |

**Verdict:** §5.2.4 remains BLOCKED. The interruption does not change the gate status — it was BLOCKED before the interruption and remains BLOCKED after. The interruption adds uncertainty but does not alter the evidence gap.

## Safety Confirmation

| Check | Method | Result |
|-------|--------|--------|
| LR remains NO-GO | `LR-AUDIT-STATUS-2026-03-05.md` | ✅ NO-GO |
| No Live-Go / Echtgeld-Go | Repo evidence, CONTROL_REGISTER | ✅ Confirmed |
| No strategy/config/runtime changes | `git diff --check` scope | ✅ This doc only |
| No synthetic evidence | Classification explicitly `interruption_record` | ✅ Honest classification |
| No silent reclassification | `interruption_record` ≠ `natural_paper_evidence` | ✅ Kept separate |
| No DB writes | Read-only session | ✅ Confirmed |

## Recommendation

| Option | Description | Recommendation |
|--------|-------------|----------------|
| **Campaign #1R** (restart) | Restart a fresh campaign with new ID, same campaign #1 slot | ✅ Preferred — cleanest restart; preserves max-3 limit |
| Campaign #2 | Skip directly to #2, consuming a campaign slot | ⚠️ Acceptable but consumes a slot unnecessarily |
| Wait for host continuity guarantee | Do not restart until host uptime is predictable | ❌ Overly conservative; host reboot is a normal event |

**Recommended next action:** Restart as Campaign #1R. Generate new campaign ID, re-check start criteria before start, and pre-document host-availability preflight before starting the observation window.

## Host-Availability Preflight (for future campaigns)

Future campaigns should include a host-availability preflight before start:

| Preflight Check | Method | Pass Criterion |
|-----------------|--------|----------------|
| Host power/sleep risk | `powercfg /lastwake` or system uptime check | Uptime > 1h, no pending sleep |
| Docker running | `docker ps` — all core services healthy | All BLUE services healthy |
| Runtime continuity guard | Schedule heartbeat check every 30min (within agent session) | Heartbeat recorded before and after |
| Host downtime fallback | Document in campaign plan: "If host becomes unavailable, campaign is HOLD_INTERRUPTED_BY_HOST_SHUTDOWN" | Pre-documented |
| Recovery plan | Document in campaign plan: "On interruption → restart as Campaign #1R or skip to #2" | Pre-documented |

## Limitations

1. **No DB evidence** — Docker was not running at reconciliation time. No `correlation_ledger` query possible. The host-down period is a black box.
2. **Estimated shutdown time** — The exact host shutdown time is not known. The range ~01:00–02:00 UTC is an inference based on no activity after 00:21 UTC merge and typical user behavior.
3. **No host logs** — Windows event logs were not inspected. The cause could be power loss, manual shutdown, sleep, or automatic update reboot. The exact cause is not relevant to the campaign classification.
4. **No synthetic evidence** — No attempt was made to reconstruct or simulate the host-down period. The interruption record is based on observable repo and system state only.
5. **Campaign #1R still subject to same constraints** — A restart only succeeds if the host remains available for the full 8h window. The preflight recommendations are advisory, not enforced.

---

## References

- #3095 — Campaign execution issue (remains OPEN)
- #3087 — Product-complete gate (remains OPEN, BLOCKED)
- #3094 — Design issue (CLOSED)
- #3098 — Original campaign evidence PR (merged)
- `docs/evidence/arvp_volatility_window_campaign_3095.md` — Campaign #1 evidence doc
- `docs/evidence/arvp_deterministic_window_production_3094.md` — Campaign policy design
- `docs/runbooks/ARVP_OPERATOR_RUNBOOK.md` — Operator runbook
- `docs/runbooks/CONTROL_REGISTER.md` — Board stage, LR NO-GO
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` — LR verdict NO-GO
