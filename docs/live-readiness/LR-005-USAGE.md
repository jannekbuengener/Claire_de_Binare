# LR-005 Usage: Live Readiness Completion Reporter

## Quick Start

**Generate JSON snapshot (stdout):**
```bash
python scripts/lr_reporter.py --json
```

**Generate Markdown snapshot (stdout):**
```bash
python scripts/lr_reporter.py --markdown
```

**Write snapshot files to disk:**
```bash
python scripts/lr_reporter.py --snapshot
# Creates: docs/live-readiness/completion_snapshot.json
#          docs/live-readiness/completion_snapshot.md
```

**Custom output directory:**
```bash
python scripts/lr_reporter.py --snapshot --output-dir /path/to/output
```

## Exit Codes

- `0` - Success
- `1` - Validation/input error (STATE/TASKS missing or invalid)
- `2` - Runtime/tool error

## Notes

- Read-only: Does not modify STATE or TASKS files
- Deterministic: Same inputs produce identical outputs
- Offline: No network calls, no GitHub API
