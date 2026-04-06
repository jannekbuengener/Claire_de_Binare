#!/bin/bash
# soak_telemetry_sidecar.sh — Host-side supplemental telemetry for LR-040 soak tests
#
# Runs on the HOST (not in a container) to capture what the containerized
# soak_monitor.sh cannot see: host disk, RAM, CPU, Docker resource usage.
#
# IMPORTANT: This is supplemental/non-canonical telemetry.
# It does NOT modify any canonical soak test artifacts.
#
# Usage:
#   bash infrastructure/scripts/soak_telemetry_sidecar.sh
#   bash infrastructure/scripts/soak_telemetry_sidecar.sh soak_test_20260401_114850
#   SOAK_RUN_ID=soak_test_20260401_114850 bash infrastructure/scripts/soak_telemetry_sidecar.sh
#
# Scheduling (Windows Task Scheduler):
#   Use artifacts/run_soak_sidecar.cmd as launcher, schedule every 15 minutes.

set -euo pipefail

ARTIFACT_ROOT="${ARTIFACT_ROOT:-artifacts}"
TIMESTAMP_FILE=$(date -u +"%Y%m%d_%H%M%S")
TIMESTAMP_HUMAN=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
HOSTNAME_VAL=$(hostname 2>/dev/null || echo "unknown")

# ── Resolve repo root and Windows drive ──────────────────────────────────────

REPO_ROOT_POSIX=$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")

# Normalize POSIX path to Windows path
if command -v cygpath >/dev/null 2>&1; then
    REPO_ROOT_WIN=$(cygpath -w "$REPO_ROOT_POSIX")
    PATH_METHOD="cygpath"
else
    # Fallback: convert /d/... to D:\...
    REPO_ROOT_WIN=$(echo "$REPO_ROOT_POSIX" | sed -E 's|^/([a-zA-Z])/|\U\1:\\|; s|/|\\|g')
    PATH_METHOD="regex-fallback"
fi

# Extract drive letter from Windows path (first character)
HOST_DRIVE="${REPO_ROOT_WIN:0:1}"

# ── Resolve soak run ID ─────────────────────────────────────────────────────

resolve_soak_run_id() {
    # Priority: argument > env var > pointer file > auto-detect

    if [ -n "${1:-}" ]; then
        SOAK_RUN_ID="$1"
        RESOLVE_METHOD="argument"
        return 0
    fi

    if [ -n "${SOAK_RUN_ID:-}" ]; then
        RESOLVE_METHOD="env var SOAK_RUN_ID"
        return 0
    fi

    local pointer_file="${ARTIFACT_ROOT}/soak_active_run_path_lr040.txt"
    if [ -f "$pointer_file" ]; then
        local pointer_content
        pointer_content=$(cat "$pointer_file" | tr -d '[:space:]')
        SOAK_RUN_ID=$(basename "$pointer_content")
        RESOLVE_METHOD="pointer file ($pointer_file)"
        return 0
    fi

    # Auto-detect: latest soak_test_* directory
    local latest
    latest=$(ls -1d "${ARTIFACT_ROOT}"/soak_test_* 2>/dev/null | sort | tail -1)
    if [ -n "$latest" ]; then
        SOAK_RUN_ID=$(basename "$latest")
        RESOLVE_METHOD="auto-detect (latest)"
        return 0
    fi

    echo "ERROR: Cannot resolve soak run ID. No argument, env var, pointer file, or soak_test_* directory found." >&2
    exit 1
}

resolve_soak_run_id "${1:-}"

# Validate the run directory exists
if [ ! -d "${ARTIFACT_ROOT}/${SOAK_RUN_ID}" ]; then
    echo "ERROR: Soak run directory not found: ${ARTIFACT_ROOT}/${SOAK_RUN_ID}" >&2
    exit 1
fi

# ── Setup sidecar output directory ───────────────────────────────────────────

SIDECAR_DIR="${ARTIFACT_ROOT}/telemetry_sidecar/${SOAK_RUN_ID}"
mkdir -p "$SIDECAR_DIR"

# Write README marker (once)
if [ ! -f "$SIDECAR_DIR/README.md" ]; then
    cat > "$SIDECAR_DIR/README.md" << 'READMEEOF'
# Telemetry Sidecar Data (Non-Canonical)

This directory contains **supplemental host-side telemetry** collected by
`soak_telemetry_sidecar.sh`. It is **NOT** part of the canonical LR-040
soak test evidence chain.

**Purpose**: Fill the observability gap left by the containerized soak monitor,
which cannot see host filesystem, RAM, or CPU metrics (e.g. `df /repo` fails
because `/repo` does not exist on the Windows host).

**Association**: The directory name mirrors the canonical soak run it supplements.
The gate evaluator (`lr040_soak_gate_eval.py`) does not read from this path.

**Safe to delete**: These files have no effect on soak test verdicts.
READMEEOF
fi

# ── Capture functions ────────────────────────────────────────────────────────
# Each function captures output into a variable. Failures are caught individually.

set +e  # Individual capture failures must not abort the script

capture_host_disk() {
    local ps_out df_out

    # Primary: PowerShell (canonical Windows disk source)
    ps_out=$(powershell.exe -NoProfile -Command "
        Get-PSDrive ${HOST_DRIVE} | Select-Object Name, Used, Free, @{N='UsedPct';E={[math]::Round(\$_.Used/(\$_.Used+\$_.Free)*100,1)}} | Format-List
    " 2>&1) || ps_out="[UNAVAILABLE: PowerShell Get-PSDrive failed: $ps_out]"

    # Secondary: df as best-effort supplement
    local df_mount
    df_mount=$(echo "$HOST_DRIVE" | tr '[:upper:]' '[:lower:]')
    df_out=$(df -h "/${df_mount}" 2>&1) || df_out="[UNAVAILABLE: df failed: $df_out]"

    HOST_DISK_CAPTURE=$(cat <<DISKEOF
--- HOST DISK ---
Source path (POSIX):   ${REPO_ROOT_POSIX}
Source path (Windows): ${REPO_ROOT_WIN}
Resolved drive:        ${HOST_DRIVE}:
Path method:           ${PATH_METHOD}

PowerShell Get-PSDrive (canonical):
${ps_out}

df (best-effort supplement):
${df_out}
DISKEOF
    )
}

capture_host_ram() {
    local ram_out
    ram_out=$(powershell.exe -NoProfile -Command "
        \$os = Get-CimInstance Win32_OperatingSystem
        [PSCustomObject]@{
            TotalMB  = [math]::Round(\$os.TotalVisibleMemorySize / 1024)
            FreeMB   = [math]::Round(\$os.FreePhysicalMemory / 1024)
            UsedMB   = [math]::Round((\$os.TotalVisibleMemorySize - \$os.FreePhysicalMemory) / 1024)
            UsedPct  = [math]::Round((\$os.TotalVisibleMemorySize - \$os.FreePhysicalMemory) / \$os.TotalVisibleMemorySize * 100, 1)
        } | Format-List
    " 2>&1) || ram_out="[UNAVAILABLE: PowerShell Win32_OperatingSystem failed: $ram_out]"

    HOST_RAM_CAPTURE=$(cat <<RAMEOF
--- HOST RAM ---
${ram_out}
RAMEOF
    )
}

capture_host_cpu() {
    local cpu_out
    cpu_out=$(powershell.exe -NoProfile -Command "
        (Get-CimInstance Win32_Processor).LoadPercentage
    " 2>&1) || cpu_out="[UNAVAILABLE: PowerShell Win32_Processor failed: $cpu_out]"

    HOST_CPU_CAPTURE=$(cat <<CPUEOF
--- HOST CPU ---
LoadPercentage: ${cpu_out}
CPUEOF
    )
}

capture_docker_disk() {
    local docker_df_out
    docker_df_out=$(docker system df 2>&1) || docker_df_out="[UNAVAILABLE: docker system df failed: $docker_df_out]"

    DOCKER_DISK_CAPTURE=$(cat <<DDEOF
--- DOCKER DISK (docker system df) ---
${docker_df_out}
DDEOF
    )
}

capture_docker_stats() {
    local stats_out
    stats_out=$(docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}" 2>&1) \
        || stats_out="[UNAVAILABLE: docker stats failed: $stats_out]"

    DOCKER_STATS_CAPTURE=$(cat <<DSEOF
--- DOCKER CONTAINER RESOURCES (docker stats --no-stream) ---
${stats_out}
DSEOF
    )
}

# ── Run all captures ─────────────────────────────────────────────────────────

capture_host_disk
capture_host_ram
capture_host_cpu
capture_docker_disk
capture_docker_stats

# ── Write capture file ───────────────────────────────────────────────────────

CAPTURE_FILE="${SIDECAR_DIR}/capture_${TIMESTAMP_FILE}.txt"

cat > "$CAPTURE_FILE" << CAPTUREEOF
================================================================================
SOAK TELEMETRY SIDECAR CAPTURE
================================================================================
Timestamp (UTC):    ${TIMESTAMP_HUMAN}
Soak Run ID:        ${SOAK_RUN_ID}
Soak Run Path:      ${ARTIFACT_ROOT}/${SOAK_RUN_ID}
Capture Host:       ${HOSTNAME_VAL}
Collector:          soak_telemetry_sidecar.sh (host-side, non-canonical)
Run ID resolved by: ${RESOLVE_METHOD}
================================================================================

${HOST_DISK_CAPTURE}

${HOST_RAM_CAPTURE}

${HOST_CPU_CAPTURE}

${DOCKER_DISK_CAPTURE}

${DOCKER_STATS_CAPTURE}

================================================================================
END CAPTURE
================================================================================
CAPTUREEOF

# ── Write summary line ───────────────────────────────────────────────────────

# Extract key metrics for one-liner summary (portable sed/awk, no grep -P)
DISK_PCT=$(echo "$HOST_DISK_CAPTURE" | sed -n 's/.*UsedPct[[:space:]]*:[[:space:]]*//p' | awk '{print $1; exit}')
DISK_PCT="${DISK_PCT:-n/a}"

RAM_PCT=$(echo "$HOST_RAM_CAPTURE" | sed -n 's/.*UsedPct[[:space:]]*:[[:space:]]*//p' | awk '{print $1; exit}')
RAM_PCT="${RAM_PCT:-n/a}"

CPU_PCT=$(echo "$HOST_CPU_CAPTURE" | sed -n 's/.*LoadPercentage:[[:space:]]*//p' | awk '{print $1; exit}')
CPU_PCT="${CPU_PCT:-n/a}"

echo "${TIMESTAMP_HUMAN} | drive=${HOST_DRIVE}: disk_used=${DISK_PCT}% | ram_used=${RAM_PCT}% | cpu=${CPU_PCT}% | run=${SOAK_RUN_ID}" \
    >> "${SIDECAR_DIR}/summary.log"

echo "Sidecar capture complete: ${CAPTURE_FILE}"
