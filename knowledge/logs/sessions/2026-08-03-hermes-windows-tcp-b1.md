# Session: #4289 Phase B1 TCP Unblock diagnostics (2026-08-03)

## Scope
Hermes→Windows Tailscale TCP diagnosis for PR #4331 / Issue #4289 Phase B1.
Plan-GO for TCP unblock + drills; merge only after green gates.

## Brain Evidence
brain_source: repo-only
brain_status: not-used
context_brain_attempted: true
context_brain_used: false
context_available: false
repo_fallback_used: true
repo_fallback_reason: unavailable
context_tool_status: absent
context_trust_level: none
records_found: none
tools_or_queries:
  - GetMcpTools / cdb_context (server absent in this workspace)
  - live Windows PowerShell + Tailscale CLI + Hermes SSH probes
  - official Tailscale docs (shields-up, prefs, PacketFilter)
repo_crosscheck:
  - infrastructure/hermes/windows/setup-sshd-hermes.ps1
  - docs/runbooks/hermes_hetzner_operations.md
impact_on_plan:
  - Do not mutate Tailnet policy (PacketFilter already allows peer TCP)
  - Fix live Port 2222 drift back to Port 22
  - Hold SSH/kill-switch/reboot drills and merge until Hermes TCP/22 PASS
limitations:
  - No SurrealDB records
  - Tailscale IPs redacted in GitHub evidence

## Live findings (redacted)
- Listener drift: live config was Port 2222 (not 22); restored Port 22 / ListenAddress 0.0.0.0
- ShieldsUp=false; syspolicy list empty; AllowIncomingConnections not forced
- Tailscale ping bidirectional PASS; Hermes→Windows TCP all ports TIMEOUT
- PacketFilter: hermes in Srcs; TCP/22 to self allowed; tstun_in_from_wg_drop_filter=0
- pktmon: Hermes SYN on Tailscale Tunnel + tcpip.sys IPv4; tx SYN-ACK count=0
- Temporary Any:22 FW allow + raw Python accept on :22 still TIMEOUT
- Local Test-NetConnection to self TS IP PASS without tunnel SYN (loopback-optimized)
- Controlled reboot: sshd-hermes Running/Automatic; TCP still TIMEOUT

## Status
HOLD_WINDOWS_FIREWALL (host TCP path after Wintun/tcpip injection; not Tailnet ACL)

Issue #4289 remains OPEN. PR #4331 remains OPEN (no merge).
