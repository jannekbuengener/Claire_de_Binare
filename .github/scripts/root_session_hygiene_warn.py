#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    kind: str
    path: str
    detail: str


SUSPICIOUS_PATTERNS = [
    (re.compile(r"(^|/)\.codex-worktree-[^/]+(/|$)"), "codex worktree artifact"),
    (re.compile(r"(^|/)codex-worktree-[^/]+(/|$)"), "codex worktree artifact"),
    (re.compile(r"(^|/)tmp[-_][^/]+(/|$)"), "tmp artifact directory"),
    (re.compile(r"(^|/)tmp[^/]*(/|$)"), "tmp artifact directory"),
    (re.compile(r"(^|/)evals(/|$)"), "eval artifact directory"),
    (re.compile(r"(^|/)\.worktrees_backup(/|$)"), "worktree backup directory"),
    (re.compile(r"(^|/)\.claude(/|$)"), "local assistant artifact path"),
    (re.compile(r"\.(log|tmp|bak)$"), "temporary file extension"),
]


def run(args: list[str]) -> str:
    proc = subprocess.run(
        args,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(args)}\n{proc.stderr.strip()}")
    return proc.stdout


def parse_name_status(base: str, head: str) -> list[tuple[str, str]]:
    out = run(["git", "diff", "--name-status", f"{base}...{head}"])
    rows: list[tuple[str, str]] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0].strip()
        if status.startswith("R") and len(parts) >= 3:
            rows.append((status, parts[2].strip()))
            continue
        if status.startswith("C") and len(parts) >= 3:
            rows.append((status, parts[2].strip()))
            continue
        if len(parts) >= 2:
            rows.append((status, parts[1].strip()))
    return rows


def collect_findings(rows: list[tuple[str, str]]) -> list[Finding]:
    findings: list[Finding] = []
    for status, path in rows:
        is_addition = status.startswith(("A", "R", "C"))
        if not is_addition:
            continue

        if "/" not in path:
            findings.append(Finding("root_addition", path, "new top-level file added in PR"))

        for pattern, detail in SUSPICIOUS_PATTERNS:
            if pattern.search(path):
                findings.append(Finding("artifact_pattern", path, detail))
                break

    dedup = {(f.kind, f.path, f.detail): f for f in findings}
    return sorted(dedup.values(), key=lambda item: (item.kind, item.path, item.detail))


def markdown(findings: list[Finding], *, base: str, head: str) -> str:
    lines = [
        "## Root/Session Hygiene Warning",
        "",
        f"- Diff scope: `{base}...{head}`",
        f"- Findings: `{len(findings)}`",
        "",
    ]
    if not findings:
        lines.extend(["No root/session hygiene warnings for this diff.", ""])
        return "\n".join(lines)

    lines.append("Potentially hygiene-relevant additions:")
    for f in findings:
        lines.append(f"- `{f.path}` ({f.kind}: {f.detail})")
    lines.append("")
    lines.append("This workflow is warning-only and does not block merge.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Warn on potential root/session hygiene drift in PR diffs.")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    args = parser.parse_args()

    rows = parse_name_status(args.base, args.head)
    findings = collect_findings(rows)

    with open(args.output_json, "w", encoding="utf-8") as fp:
        json.dump(
            {"base": args.base, "head": args.head, "findings": [f.__dict__ for f in findings]},
            fp,
            indent=2,
        )
        fp.write("\n")

    with open(args.output_md, "w", encoding="utf-8") as fp:
        fp.write(markdown(findings, base=args.base, head=args.head))

    for f in findings:
        print(f"::warning file={f.path}::root-session-hygiene warning ({f.kind}): {f.detail}")

    print(f"root-session-hygiene findings: {len(findings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
