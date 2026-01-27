# tools/planning/planning_lint.py
# Purpose: detect planning/document fragmentation regressions (phase/milestone/gap conventions).
#
# Stdlib only. Designed to be run locally or in CI.

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Dict, Tuple

PHASE_RE = re.compile(r"\b(phase|phasen)\s*[:#-]?\s*(\d+)\b", re.IGNORECASE)
MILESTONE_RE = re.compile(r"\b(alpha|beta|gamma)\b", re.IGNORECASE)
GAP_RE = re.compile(r"\bGAP[-_ ]?0*(\d+)\b", re.IGNORECASE)

DEFAULT_TASK_LINE_RE = r"^\s*[-*]\s+.+$"  # bullet-like


@dataclass
class FileScan:
    path: str
    sha256: str
    phase_numbers: List[int]
    milestones: List[str]
    gap_refs: List[int]
    gap_ref_count: int
    task_lines_total: int
    task_lines_missing_gap: int


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def scan_file(p: Path, require_gap_per_task_line: bool, task_line_pattern: re.Pattern) -> FileScan:
    text = p.read_text(encoding="utf-8", errors="replace")
    phases = [int(m.group(2)) for m in PHASE_RE.finditer(text)]
    milestones = [m.group(1).lower() for m in MILESTONE_RE.finditer(text)]
    gaps = [int(m.group(1)) for m in GAP_RE.finditer(text)]

    task_total = 0
    task_missing = 0
    if require_gap_per_task_line:
        for line in text.splitlines():
            if task_line_pattern.search(line):
                task_total += 1
                if not GAP_RE.search(line):
                    task_missing += 1

    return FileScan(
        path=str(p),
        sha256=sha256(p),
        phase_numbers=sorted(set(phases)),
        milestones=sorted(set(milestones)),
        gap_refs=sorted(set(gaps)),
        gap_ref_count=len(gaps),
        task_lines_total=task_total,
        task_lines_missing_gap=task_missing,
    )


def normalize_sources(sources: Iterable[str]) -> List[Path]:
    out: List[Path] = []
    for s in sources:
        p = Path(s)
        if p.is_dir():
            for ext in ("*.md", "*.txt"):
                out.extend(sorted(p.rglob(ext)))
        else:
            out.append(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="CDB Planning Doc Lint (phase/gap/milestone conventions)")
    ap.add_argument("--sources", nargs="+", required=True,
                    help="List of markdown/text files OR directories (dirs will be recursively scanned for *.md/*.txt).")
    ap.add_argument("--out", required=True, help="Output JSON report path.")
    ap.add_argument("--require-gap-per-task-line", action="store_true",
                    help="If set, every bullet-like line must contain a GAP-XXX reference.")
    ap.add_argument("--task-line-regex", default=DEFAULT_TASK_LINE_RE,
                    help=f"Regex for 'task-like' lines. Default: {DEFAULT_TASK_LINE_RE!r}")
    args = ap.parse_args()

    files = normalize_sources(args.sources)
    missing = [str(p) for p in files if not p.exists()]
    if missing:
        raise SystemExit(f"Missing source files: {missing}")

    task_line_pattern = re.compile(args.task_line_regex)
    scans = [scan_file(p, args.require_gap_per_task_line, task_line_pattern) for p in files]

    phase_sets: List[Tuple[int, ...]] = [tuple(s.phase_numbers) for s in scans]
    non_empty_phase_sets = [ps for ps in phase_sets if len(ps) > 0]
    phase_consistent = (len(set(non_empty_phase_sets)) <= 1)  # allow empty docs

    gap_rule_violations = sum(s.task_lines_missing_gap for s in scans)

    report: Dict[str, object] = {
        "phase_consistent": phase_consistent,
        "phase_sets": phase_sets,
        "uses_alpha_beta_gamma": any(len(s.milestones) > 0 for s in scans),
        "require_gap_per_task_line": bool(args.require_gap_per_task_line),
        "gap_rule_violations": int(gap_rule_violations),
        "files": [asdict(s) for s in scans],
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if not phase_consistent:
        return 2
    if args.require_gap_per_task_line and gap_rule_violations > 0:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
