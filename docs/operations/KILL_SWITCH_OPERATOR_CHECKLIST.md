# Kill-Switch Operator Checklist

Status:
- Repo-native successor to the former `tools/test_pack/runbooks/kill_switch_checklist.md`
- Operational reference for manual kill-switch precheck and toggle verification
- Not a replacement for the repo-native drill canon under `scripts/drills/` + `tests/chaos/`

Purpose:
- Verify that the kill-switch is inactive before canary or soak activity
- Give operators one current reference for manual activate / verify / deactivate flows
- Avoid stale pack-specific assumptions such as port `5000`, `LR-003`, or `tools/test_pack/` script wiring

## Default Local Endpoint

- Local BLUE runtime risk service: `http://127.0.0.1:8002`

## Pre-Run Kill-Switch Check

Required outcome before start:
- `active: false`

HTTP check:

```bash
curl -s http://127.0.0.1:8002/kill-switch
```

Expected shape:

```json
{"active": false, "reason": "...", "message": "...", "activated_at": null}
```

Python fallback when the HTTP endpoint is unavailable:

```bash
python -c "from core.safety.kill_switch import get_kill_switch_details; active, reason, message, activated_at = get_kill_switch_details(create_if_missing=False); print({'active': active, 'reason': reason, 'message': message, 'activated_at': activated_at})"
```

## Optional Manual Toggle Verification

Activate:

```bash
curl -s -X POST http://127.0.0.1:8002/kill-switch/activate \
  -H "Content-Type: application/json" \
  -d '{"reason":"manual","message":"Operator verification","operator":"<your-name>"}'
```

Verify active:

```bash
curl -s http://127.0.0.1:8002/kill-switch
```

Expected outcome:
- `active: true`

Deactivate:

```bash
curl -s -X POST http://127.0.0.1:8002/kill-switch/deactivate \
  -H "Content-Type: application/json" \
  -d '{"operator":"<your-name>","justification":"Verification complete"}'
```

Verify inactive again:

```bash
curl -s http://127.0.0.1:8002/kill-switch
```

Expected outcome:
- `active: false`

## Evidence To Keep

- UTC timestamp of the precheck
- Operator name
- Saved response from the final inactive status check
- If used for canary/soak gating: keep the matching `risk_status.json` artifact that later feeds `soak_gate_eval.py`

## Limits

- This checklist does not prove end-to-end order-flow stop under live runtime conditions.
- This checklist does not revive `tools/test_pack/` as an active harness.
- Repo-native drill canon remains `scripts/drills/` + `tests/chaos/`.
