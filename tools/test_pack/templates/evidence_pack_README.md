# Evidence Pack (Template)

Status:
- Frozen pack-local template under `tools/test_pack/`
- Kept as historical utility inside the frozen import snapshot
- Not promoted to a repo-wide canonical template in this follow-up cut

Path convention:
docs/ops/evidence/YYYY-MM-DD_PHASEX_<topic>/

Required artifacts:
- README.md (this file, filled in)
- sources_manifest.txt (all inputs + hashes)
- run_config.json (all runtime parameters + versions)
- logs/ or service_logs/ (raw logs)
- reports/ (JSON metrics + assertion outputs)
- screenshots/ (if applicable)
- hashes.txt (optional: hashes of large artifacts)

## Run Summary
- Date/Time (UTC):
- Commit/Ref:
- Environment (local/CI):
- Operator (if drill):

## What was executed
- Command(s):
- Scenario/Seed (if chaos):
- Expected outcomes:

## Results
- PASS/FAIL:
- Key metrics:
- Links to raw artifacts:

## Notes / Deviations
- Any deviations from standard runbook:
- Known gaps / TODOs:
