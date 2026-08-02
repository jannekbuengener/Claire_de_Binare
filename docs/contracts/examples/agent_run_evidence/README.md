# Agent Run Evidence examples (#4256)

| File | Purpose |
|---|---|
| `positive_mock_pass_bundle.json` | Valid sealed mock PASS bundle |
| `negative_unknown_field.json` | Same bundle with an unknown top-level field (schema reject) |

Generate or refresh the positive fixture via:

```text
python -m tools.agent_control evidence emit --run <ID> --state <PATH>
```

Do not commit runtime JSONL stores under `artifacts/agent-control/evidence/`.
