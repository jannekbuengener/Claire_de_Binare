# Command Manifest

Scope: `#2951` only.

No command in this pack was allowed to:
- place a real order
- touch a live or testnet venue
- mutate exchange, broker, account, DB, or MCP state
- print secret values

## GitHub live reads

| Command / surface | Purpose | Outcome |
| --- | --- | --- |
| `git fetch origin --prune` | refresh `origin/main` before branching | success |
| `gh issue view 2951 --json ...` | confirm issue truth and scope | `#2951 OPEN`; no prior runtime evidence delivered |
| `gh pr list --state open --json ...` | detect existing PR / lock collision | `[]`; no open PR to continue |
| `gh issue view 1445 --json ...` | control-first live anchor | confirms `#1445` as cockpit anchor and `NO-GO` posture |
| `gh issue view 1492 --json ...` | separate Stage from LR | confirms historical stage ratification only; not live-go |
| `gh issue view 2689 --json ...` | dedupe Gordon cleanup follow-up | `#2689 CLOSED`; active Gordon remnants remain outside `#2951` scope |

## Repo / config inspection

| Command / surface | Purpose | Outcome |
| --- | --- | --- |
| `git status -sb` | verify clean start surface | clean branch surface |
| `git rev-parse HEAD` | anchor repo state | `4d332b0ffe6cb32bd02505c9fff38326d75e4c04` |
| `git rev-parse origin/main` | anchor live base | `4d332b0ffe6cb32bd02505c9fff38326d75e4c04` |
| `git worktree list` | verify no extra writer surface | single worktree only |
| `set DRY_RUN` and peers | inspect current shell overrides | all relevant flags unset |
| `type services/execution/config.py` | read runtime defaults | `MOCK_TRADING=true`, `DRY_RUN=true`, `MEXC_TESTNET=true` defaults |
| `rg -n ... services/execution/service.py` | inspect active execution path | `TRADING_MODE` logged only; `_require_live_confirmation()` gates unsafe mainnet tuple |
| `rg -n ... services/execution/live_executor.py core/clients/mexc.py` | inspect send vs dry-run branch | `dry_run=True` keeps `client=None`; send path calls `place_market_order` / `place_limit_order` only when not dry-run |
| `rg -n ... core/config/trading_mode.py` | inspect legacy staged map | `STAGED -> MOCK_TRADING=false, DRY_RUN=false, MEXC_TESTNET=true`; not acceptable as dry-run proof on active path |
| `rg -n ... infrastructure/compose/compose.blue.yml .env.example` | inspect repo defaults | compose default `MOCK_TRADING: "true"`; `.env.example` keeps `MEXC_TESTNET=true`, `MOCK_TRADING=true`, `DRY_RUN=true` |

## Dry-run / guard validation commands

| Command / surface | Purpose | Outcome |
| --- | --- | --- |
| `pytest -q tests/...` with default temp | initial targeted validation | 31 passed / 35 environment errors due temp ACL; not a product regression |
| `pytest -q --basetemp .tmp\\pytest-lr050-runtime-dry-run tests\\unit\\services\\test_execution_shadow_gate.py tests\\unit\\risk\\test_kill_switch_endpoints.py tests\\unit\\risk\\test_contract_enforcement.py tests\\unit\\safety\\test_kill_switch.py` | repo-local deterministic evidence run | `66 passed, 104 warnings, 0 failures` |
| interactive `python` harness for `LiveExecutor(dry_run=True, testnet=True)` | direct non-send executor proof without stack start | `client_is_none=true`, `order_id=DRY_RUN_lr050-cli-1`, `status=FILLED` simulated |

## Commands intentionally not executed

| Withheld command class | Why withheld |
| --- | --- |
| `docker compose up`, service starts, stack restarts | broader than `#2951`, runtime mutation surface too wide |
| balance / account / auth checks against MEXC | would require real secrets or exchange touch |
| any `place_*` or `DRY_RUN=false` executor call | violates non-send boundary |
| receiver proof / Alertmanager delivery drills | separate blocker and separate runtime scope |
| live or testnet venue probes | `MEXC_TESTNET` is not non-send proof |
