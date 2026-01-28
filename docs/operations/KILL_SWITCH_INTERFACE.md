# KILL_SWITCH_INTERFACE.md

**Status:** Draft / Interface Definition
**Issue:** #657

## 1. Interface (Make Targets)

The system MUST support the following high-level commands for "One Button" operation.

| Command | Purpose | Expected Outcome |
|---------|---------|------------------|
| `make kill-switch-activate` | **EMERGENCY STOP** | - All trading HALTED immediately<br>- Alert triggered<br>- Evidence generated |
| `make kill-switch-status` | **STATUS CHECK** | - Returns active/inactive state<br>- Checks File & Redis (Single Source) |
| `make kill-switch-release` | **RESUME TRADING** | - Requires operator confirmation<br>- Logs resumption event |

## 2. Implementation Requirements

- **Atomic:** Must update Single Source of Truth (see #722) reliably.
- **Verifiable:** Must return exit code 0 only if system is TRULY stopped.
- **Evidence:** Must produce `timeline.json` in `evidence/drills/` or `evidence/emergency/`.

## 3. Usage

```bash
# In case of emergency:
make kill-switch-activate

# To check status:
make kill-switch-status
```
