# Codex Prompt — Import & Wire CDB Test Pack v2 into Repo (local → PR)

Context:
- We work **local → remote**.
- Do **not** edit governance constitution/policies unless explicitly asked.
- Goal: integrate the already-built test pack ZIP into the repo in a clean, upgradeable way.

Inputs (local Windows):
- Test pack ZIP: `D:\Dev\Workspaces\Prompts\TEST\cdb_test_pack_v2.zip`
- Prompt folder: `D:\Dev\Workspaces\Prompts\TEST`
- Target repo (assume already cloned): `D:\Dev\Workspaces\Repos\Claire_de_Binare`
  - If the repo path differs, discover it via `git rev-parse --show-toplevel`.

Deliverable:
- A single PR that adds the Test Pack v2 into the repo under a stable path, plus a minimal wiring layer and docs:
  - Copy test pack to: `tools/test_pack/` (or `tests/test_pack/` if you prefer—pick ONE and document it)
  - Add a short README in that folder explaining how to run locally (PowerShell) and how to generate an evidence pack.
  - Add a “smoke” CI job that runs only the planning lint + scenario generation (NO docker compose up in CI yet).

Hard rules:
- No “TODO-only” PR. Every script must at least run and produce outputs (even if adapters are stubs).
- Keep changes surgical: add files + minimal integration. Don’t refactor existing system code.
- No internet access assumptions.

Steps:
1) Create a new branch:
   - `git checkout -b testpack/import-v2`
2) Unzip the pack into a temp folder:
   - `Expand-Archive -Path "D:\Dev\Workspaces\Prompts\TEST\cdb_test_pack_v2.zip" -DestinationPath "$env:TEMP\cdb_test_pack_v2" -Force`
3) Copy contents into repo target folder (choose ONE target root and stick to it):
   - `Copy-Item -Recurse -Force "$env:TEMP\cdb_test_pack_v2\*" "<REPO>\tools\test_pack\"`
4) Normalize line endings if needed (no CRLF surprises).
5) Add a top-level integration doc entry:
   - In repo README or docs index (whichever is appropriate), add a short “Testing: Chaos/Drills” link pointing to `tools/test_pack/README.md`.
6) Add a tiny “adapter contract” file that declares where the hooks will connect:
   - Example: `tools/test_pack/adapters/ADAPTERS.md` describing:
     - ingestion path (HTTP vs stream vs file) = **NOT selected yet**
     - metrics snapshot source (Prometheus vs endpoint) = **NOT selected yet**
     - kill-switch verification source (metric/log/state endpoint) = **NOT selected yet**
   - This document is the single source of truth so later we can kill TODO drift.
7) CI smoke job:
   - Add a workflow (or extend existing) to run:
     - `python tools/test_pack/tools/planning/planning_lint.py --sources <some docs folder> --out <artifact>`
       - If actual planning docs paths are unknown, run it on `tools/test_pack/README.md` just to prove the pipeline works, but clearly document how to point it at real docs.
     - `python tools/test_pack/tools/chaos/generate_scenario.py --mode whipsaw --minutes 30 --seed 1337 --out <artifact>`
   - Upload artifacts.
   - Do NOT attempt docker compose in CI.
8) Validate locally:
   - `python ...planning_lint.py ...`
   - `python ...generate_scenario.py ...`
   - Ensure scripts exit 0.
9) Commit with message:
   - `feat(testpack): import CDB test pack v2 + CI smoke`
10) Push branch and open PR. Include in PR body:
   - What was added
   - How to run locally
   - What remains intentionally un-wired (ingestion/metrics/kill-switch verification) and why

Acceptance criteria (must be true):
- Repo contains `tools/test_pack/` (or chosen location) with all test pack files.
- `planning_lint.py` runs and outputs JSON.
- `generate_scenario.py` runs and outputs JSONL.
- CI has a green “Test Pack Smoke” job producing the two artifacts.
- Docs link exists and points to the new README.
- No changes to core trading services or governance canon.

Output required:
- PR link
- List of changed files
- Local commands to run the pack after merge
