#!/usr/bin/env python3
"""
Shadow Mode Daily Digest Generator
Generates executive summary for last 24h (UTC) with status ampel, KPIs, incidents, actions.

Usage:
    python scripts/generate_shadow_digest.py [--date YYYY-MM-DD] [--email]

Options:
    --date YYYY-MM-DD    Generate digest for specific date (default: today UTC)
    --email              Send digest via email (requires SMTP config)
"""

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def run_command(cmd: List[str], check: bool = True) -> Tuple[str, int]:
    """Run shell command and return output."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=check, shell=False
        )
        return result.stdout.strip(), result.returncode
    except subprocess.CalledProcessError as e:
        return e.stderr.strip(), e.returncode


def prometheus_query(query: str) -> Optional[float]:
    """Query Prometheus instant API and return scalar value."""
    cmd = [
        "docker", "exec", "cdb_prometheus",
        "wget", "-qO-", f"http://localhost:9090/api/v1/query?query={query}"
    ]
    output, code = run_command(cmd, check=False)
    if code != 0:
        return None

    try:
        data = json.loads(output)
        if data["status"] == "success" and data["data"]["result"]:
            return float(data["data"]["result"][0]["value"][1])
    except (json.JSONDecodeError, KeyError, IndexError, ValueError):
        logging.getLogger(__name__).debug("Prometheus query result parse failed, returning None", exc_info=True)
    return None


def get_24h_metrics() -> Dict[str, float]:
    """Collect 24h metrics from Prometheus."""
    queries = {
        "signals_total": "increase(signals_received_total[24h])",
        "approvals_total": "increase(orders_approved_total[24h])",
        "blocked_total": "increase(orders_blocked_total[24h])",
        "trades_filled": "increase(execution_orders_filled_total[24h])",
        "trades_rejected": "increase(execution_orders_rejected_total[24h])",
    }

    metrics = {}
    for name, query in queries.items():
        value = prometheus_query(query)
        metrics[name] = value if value is not None else 0.0

    # Calculate approval rate
    total_orders = metrics["approvals_total"] + metrics["blocked_total"]
    metrics["approval_rate"] = (
        (metrics["approvals_total"] / total_orders * 100)
        if total_orders > 0
        else 0.0
    )

    return metrics


def get_active_alerts() -> List[Dict]:
    """Get active alerts from Prometheus."""
    cmd = [
        "docker", "exec", "cdb_prometheus",
        "wget", "-qO-", "http://localhost:9090/api/v1/alerts"
    ]
    output, code = run_command(cmd, check=False)
    if code != 0:
        return []

    try:
        data = json.loads(output)
        if data["status"] == "success":
            return data["data"]["alerts"]
    except (json.JSONDecodeError, KeyError):
        logging.getLogger(__name__).debug("Prometheus alerts parse failed, returning empty list", exc_info=True)
    return []


def summarize_alerts(alerts: List[Dict]) -> List[Dict]:
    """Summarize alerts by name, count, max severity."""
    summary = {}
    for alert in alerts:
        name = alert["labels"].get("alertname", "Unknown")
        severity = alert["labels"].get("severity", "unknown")
        state = alert["state"]

        if name not in summary:
            summary[name] = {"count": 0, "max_severity": severity, "states": []}

        summary[name]["count"] += 1
        summary[name]["states"].append(state)

        # Update max severity (critical > warning > unknown)
        if severity == "critical" or summary[name]["max_severity"] != "critical":
            summary[name]["max_severity"] = severity

    # Convert to list and sort by severity then count
    result = [
        {"name": name, "count": data["count"], "severity": data["max_severity"]}
        for name, data in summary.items()
    ]
    result.sort(key=lambda x: (x["severity"] != "critical", -x["count"]))
    return result[:3]  # Top 3


def get_git_changes() -> List[str]:
    """Get git commits from last 24h."""
    cmd = [
        "git", "log", "--since=24.hours", "--oneline", "--no-merges",
        "--format=%h %s"
    ]
    output, code = run_command(cmd, check=False)
    if code != 0:
        return []
    return [line for line in output.split("\n") if line.strip()]


def determine_status(metrics: Dict[str, float], alerts: List[Dict]) -> Tuple[str, str]:
    """Determine status ampel (GREEN/YELLOW/RED) and reason."""
    # Check for critical alerts
    critical_alerts = [a for a in alerts if a["labels"].get("severity") == "critical" and a["state"] == "firing"]
    if critical_alerts:
        return "RED", f"{len(critical_alerts)} critical alert(s) firing"

    # Check approval rate
    if metrics["approval_rate"] < 10:
        return "RED", f"Approval rate critically low: {metrics['approval_rate']:.1f}%"

    # Check if pipeline is stalled
    if metrics["signals_total"] > 100 and metrics["trades_filled"] == 0:
        return "YELLOW", "Pipeline stalled: signals flowing but no trades"

    # Check for warning alerts
    warning_alerts = [a for a in alerts if a["labels"].get("severity") == "warning" and a["state"] in ["pending", "firing"]]
    if len(warning_alerts) > 3:
        return "YELLOW", f"{len(warning_alerts)} warning alerts active"

    # All good
    if metrics["trades_filled"] > 0 and metrics["approval_rate"] > 50:
        return "GREEN", "Normal operation: trades flowing, approval rate healthy"

    return "YELLOW", "Degraded operation: low activity or approval rate"


def generate_digest(date_str: str, metrics: Dict[str, float], alerts: List[Dict], git_changes: List[str]) -> str:
    """Generate markdown digest."""
    status, reason = determine_status(metrics, alerts)
    alert_summary = summarize_alerts(alerts)

    # Format alert summary
    alert_lines = []
    for alert in alert_summary:
        alert_lines.append(f"   - {alert['name']}: {alert['count']} (severity: {alert['severity']})")
    alert_text = "\n".join(alert_lines) if alert_lines else "   - No active alerts"

    # Format git changes
    git_lines = []
    for change in git_changes[:5]:  # Top 5 commits
        git_lines.append(f"   - {change}")
    git_text = "\n".join(git_lines) if git_lines else "   - No commits in last 24h"

    # Incidents section
    incidents_text = "   - None detected"
    if status == "RED":
        incidents_text = f"   - **{reason}** (active now)"
    elif status == "YELLOW" and "stalled" in reason.lower():
        incidents_text = f"   - **{reason}** (under investigation)"

    # Actions needed
    actions_needed = []
    if status == "RED":
        actions_needed.append("**URGENT:** Resolve critical alerts")
    if metrics["approval_rate"] < 10:
        actions_needed.append("**WARNING:** Investigate low approval rate (< 10%)")
    if metrics["signals_total"] > 100 and metrics["trades_filled"] == 0:
        actions_needed.append("**WARNING:** Fix pipeline stall (signals flowing, zero trades)")
    if not actions_needed:
        actions_needed.append("Continue monitoring")
    actions_text = "\n".join([f"   - {a}" for a in actions_needed[:3]])

    # Generate markdown
    markdown = f"""# Shadow Mode Daily Digest - {date_str}

**Report Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

---

## Status: {status}

**{reason}**

---

## KPIs (Last 24h)

### Signal Flow
- **Signals Received:** {int(metrics['signals_total'])}
- **Orders Approved:** {int(metrics['approvals_total'])}
- **Orders Blocked:** {int(metrics['blocked_total'])}
- **Approval Rate:** {metrics['approval_rate']:.1f}%

### Execution
- **Trades Filled:** {int(metrics['trades_filled'])}
- **Trades Rejected:** {int(metrics['trades_rejected'])}
- **Fill Rate:** {(metrics['trades_filled'] / max(1, metrics['approvals_total']) * 100):.1f}%

---

## Top 3 Alerts (24h)

{alert_text}

---

## Incidents / Breakpoints

{incidents_text}

---

## Actions

### Changes Today
{git_text}

### Decisions Needed Tomorrow
{actions_text}

---

## Evidence Commands

**Reproduce this report:**
```bash
# Run digest generator
python scripts/generate_shadow_digest.py --date {date_str}

# Manual data collection:
# 24h signals
docker exec cdb_prometheus wget -qO- "http://localhost:9090/api/v1/query?query=increase(signals_received_total[24h])"

# Active alerts
docker exec cdb_prometheus wget -qO- "http://localhost:9090/api/v1/alerts"

# Git changes
git log --since=24.hours --oneline --no-merges
```

---

*Auto-generated by Shadow Mode Digest Script*
"""
    return markdown


def send_email(digest_path: Path) -> bool:
    """Send digest via email (optional)."""
    # Check if email command exists
    cmd_check = ["docker", "ps", "--filter", "name=cdb_grafana", "--format", "{{.Names}}"]
    output, code = run_command(cmd_check, check=False)
    if code != 0 or "cdb_grafana" not in output:
        print("Email sending not available (Grafana not running)")
        return False

    print("Email sending via Grafana SMTP (implement if needed)")
    return False  # Not implemented yet


def main():
    parser = argparse.ArgumentParser(description="Generate Shadow Mode Daily Digest")
    parser.add_argument(
        "--date",
        type=str,
        default=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        help="Date for digest (YYYY-MM-DD, default: today UTC)"
    )
    parser.add_argument(
        "--email",
        action="store_true",
        help="Send digest via email"
    )
    args = parser.parse_args()

    # Validate date format
    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print(f"Error: Invalid date format '{args.date}'. Use YYYY-MM-DD")
        sys.exit(1)

    print(f"Generating Shadow Mode Daily Digest for {args.date}...")

    # Collect data
    print("  Collecting metrics from Prometheus...")
    metrics = get_24h_metrics()

    print("  Collecting alerts from Prometheus...")
    alerts = get_active_alerts()

    print("  Collecting git changes...")
    git_changes = get_git_changes()

    # Generate digest
    print("  Generating digest markdown...")
    digest_content = generate_digest(args.date, metrics, alerts, git_changes)

    # Write to file
    output_dir = Path("reports/shadow_mode")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"DAILY_DIGEST_{args.date}.md"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(digest_content)

    print(f"[OK] Digest generated: {output_path}")

    # Optional: Send email
    if args.email:
        print("  Sending email...")
        if send_email(output_path):
            print("[OK] Email sent")
        else:
            print("[SKIP] Email sending skipped")

    return 0


if __name__ == "__main__":
    sys.exit(main())
