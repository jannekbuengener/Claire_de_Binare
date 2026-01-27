# Kill-Switch Checklist (1-page)

Goal: stop order flow safely and verifiably.

Preconditions:
- You know the correct environment (paper/live).
- You have credentials/access ready.
- You have the incident channel open.

Steps (record timestamps):
1) Acknowledge alert (if your process requires it).
2) Confirm this is not a false positive (max 5 seconds).
3) Activate kill switch:
   - Method: {API|UI|CLI}
   - Command/Action: {fill in exact command}
4) Verify "order flow stopped":
   - No new orders after activation timestamp
   - Open orders canceled/frozen per design
   - System state reflects STOP/HALT
5) Announce status in incident channel:
   - 'Kill-switch active' + time
   - Verification result
6) Preserve evidence:
   - screenshot(s)
   - logs snapshot
   - timeline.json

Post-Drill:
- What slowed you down?
- Any ambiguous runbook step?
- Any missing observability hook?
