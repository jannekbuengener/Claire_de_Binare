# LR-050 Runtime Dry-Run Evidence Pack

Status: non-destructive evidence pack assembled for `#2951`; LR remains `NO-GO`.

## Scope

- issue: `#2951`
- runtime-go scope: non-destructive only
- no real orders
- no exchange or broker mutation
- no productive DB writes
- no secret reads or outputs
- no Gordon gate used

## Live / control truth

- `#2951` is `OPEN`
- there was no open PR to continue
- `#1445` remains the control-first cockpit anchor
- `#1492` remains historical stage ratification only
- LR stays `NO-GO`

## Main findings

1. Current shell overrides for the relevant execution flags were all unset.
2. Repo defaults keep `MOCK_TRADING=true` and `DRY_RUN=true`.
3. `TRADING_MODE=staged` is not valid dry-run proof on the active execution path.
4. `MEXC_TESTNET=true` is not valid non-send proof.
5. A direct `LiveExecutor(dry_run=True)` harness produced a `DRY_RUN_*` result with no client instantiation.
6. Targeted non-destructive guard tests passed cleanly once `pytest` used a repo-local temp root:
   - `66 passed, 104 warnings`

## Main blockers that remain open

- venue / endpoint semantics external verification
- canary numeric caps and symbols
- full order-builder runtime path
- receiver proof / operator receipt
- exact human live-capital approval

## Gordon decommission handling

- No Gordon gate was used.
- `#2689` already exists and is closed.
- Active Gordon remnants remain in some non-`#2951` docs and decision records.
- Those remnants do not block this evidence pack, but they still warrant a narrow deduped follow-up because active docs still mention Gordon for Docker / compose changes.

## Environment limitations encountered

- PowerShell-based local exec was unusable in this session due `CreateProcessAsUserW failed: 1312`.
- `pytest` default temp roots outside the repo were not writable.
- Both limitations were worked around without widening runtime scope:
  - `cmd.exe` fallback
  - repo-local `--basetemp .tmp\pytest-lr050-runtime-dry-run`

## Conservative conclusion

This pack proves a narrow non-send command surface for `#2951` and upgrades the runtime discussion from docs-only to repo-backed local evidence. It does not clear the live blockers and does not move LR beyond `NO-GO`.
