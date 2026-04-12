# CDB Test Pack v2 (Frozen Import Snapshot)

Status:
- Frozen experimental / import snapshot.
- Not maintained as an active repo path.
- Not the canonical repo-wide 431C drill/simulation source of truth.
- The canonical repo-native line is `scripts/drills/` plus `tests/chaos/`.
- Do not add new operational or governance anchors into this pack.
- Active checklist references were moved to repo-native docs under `docs/operations/`.

This pack is a portable “safety + readiness” experiment layer before anything touches a real market.

It is built around four things you can prove with evidence packs:
1) Planning consistency (do we all mean the same thing?)
2) Chaos drills (does the system stay safe under stress?)
3) Operator drills (can a human stop it fast, every time?)
4) Mock exchange (realistic order lifecycle without real money)

## What you get
- Deterministic scenario generator (JSONL)
- Harness scripts that produce an Evidence Pack folder
- Templates for assertions and evidence documentation
- A tiny Mock Exchange server (stdlib-only) as a drop-in test target

## Pack-local run order
1) Planning lint → baseline “we’re aligned”
2) Mock Exchange smoke → baseline “order lifecycle works”
3) Chaos drill → baseline “risk + safeguards hold”
4) Kill-switch drill → baseline “human can stop it”

## Quickstart (Windows / PowerShell)
Requirements:
- Python 3.10+
- PowerShell 7+

Note:
- The commands below are pack-local examples, not the canonical repo-wide 431C drill path.

### Generate a scenario
```powershell
python tools/chaos/generate_scenario.py --mode highvol_noise --minutes 180 --seed 1337 --out .\scenario_noise.jsonl
```

### Run a chaos drill (creates an evidence pack)
```powershell
.\infrastructure\scripts\run-chaos-drill.ps1 `
  -ScenarioFile .\scenario_noise.jsonl `
  -EvidenceDir .\evidence\2026-01-26_S-CHAOS-001 `
  -RedisHost 127.0.0.1 -RedisPort 6379 `
  -PromUrl http://127.0.0.1:19090
```

### Run the operator kill-switch drill (creates an evidence pack)
```powershell
.\tools\drills\trigger-operator-drill.ps1 -EvidenceDir .\evidence\2026-01-26_S-OPS-001
```

### Run the mock exchange (for order lifecycle tests)
```powershell
python tools\mock_exchange\mock_exchange.py --port 18080
# health: http://127.0.0.1:18080/health
```

## Where to extend next
- Expand assertions in `tools/assertions/evaluate_assertions.py` for your gates
- Add additional Prometheus queries in `tools/metrics/metrics_snapshot.py`
- Add more scenarios in `scenarios/catalog.yaml`

---

## mock_exchange nested repo (`tools/test_pack/mock_exchange/`)

> **Status:** Local reference copy — not integrated, not staged, gitignored. (#1645 Slice A, #1648)

### What it is

`tools/test_pack/mock_exchange/` is a local clone of
[`github.com/didac-crst/mockexchange`](https://github.com/didac-crst/mockexchange) v0.1.5.
It is a **full paper-trading platform** (MockX Engine + Oracle + Periscope) —
a dockerized, ccxt-compatible exchange emulator backed by Valkey/Redis.

This is **distinct** from the pack-local `tools/mock_exchange/mock_exchange.py` (stdlib-only,
no dependencies) used in the quickstart above.

### Why it is gitignored

The path contains its own `.git` directory and remote. Staging it without explicit intent
would create a mode-160000 gitlink (broken submodule reference). It was added to `.gitignore`
in `#1645 Slice A` to prevent accidental staging.

### Current handling decision

**Option chosen: keep as local reference copy, no active CDB integration yet.**

Rationale:
- CDB has no concrete current test/adapter use case that requires the full Docker stack.
- The simpler pack-local mock (`tools/mock_exchange/mock_exchange.py`) covers existing
  order-lifecycle smoke tests adequately.
- The full suite (Engine + Oracle + Periscope + Valkey) adds a heavyweight Docker dependency
  that is not justified without a specific integration target.
- The path is browsable locally as a reference without any Git or build risk.

### Future integration path (when a concrete use case emerges)

If CDB needs the Engine package for adapter or backtest testing, install directly from the
upstream Git tag — **do not commit the nested repo**:

```bash
# Engine only (headless exchange emulator + REST API)
pip install "git+https://github.com/didac-crst/mockexchange.git@v0.1.5#subdirectory=packages/engine"

# Oracle only (price feed service)
pip install "git+https://github.com/didac-crst/mockexchange.git@v0.1.5#subdirectory=packages/oracle"
```

Add the chosen package to the relevant `requirements*.txt` with the exact tag pinned.
Open a dedicated issue before doing so (tracked under `#1648`).

### What must NOT happen

- Do not `git add tools/test_pack/mock_exchange/` — the `.gitignore` entry prevents this.
- Do not introduce it as a Git submodule without explicit intent and a dedicated issue.
- Do not remove the local copy without first deciding whether the pip-from-tag path is ready.
