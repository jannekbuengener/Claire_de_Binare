#!/usr/bin/env python3
import argparse
import re
from pathlib import Path


UNDERLINE_H1 = re.compile(r"^(?P<title>.+?)\r?\n(=+)\s*$", re.M)
UNDERLINE_H2 = re.compile(r"^(?P<title>.+?)\r?\n(-+)\s*$", re.M)
TRAIL_WS = re.compile(r"[ \t]+(\r?\n)")


def normalize_text(md: str) -> str:
    # 1) Setext (=== / ---) -> ATX
    md = UNDERLINE_H1.sub(lambda m: f"# {m.group('title').strip()}\n", md)
    md = UNDERLINE_H2.sub(lambda m: f"## {m.group('title').strip()}\n", md)
    # 2) Trim trailing spaces
    md = TRAIL_WS.sub(r"\1", md)

    # 3) Ensure only one H1 at the top (keep the first)
    lines = md.splitlines()
    h1_indices = [i for i, ln in enumerate(lines) if ln.startswith("# ")]
    if len(h1_indices) > 1:
        first = h1_indices[0]
        for idx in h1_indices[1:]:
            if lines[idx].startswith("# "):
                lines[idx] = "## " + lines[idx][2:].lstrip()
        md = "\n".join(lines)

    return md


def process_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="ignore")
    new = normalize_text(text)
    if new != text:
        path.write_text(new, encoding="utf-8")
        return True
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Normalize Markdown headings (ATX style, trimmed)."
    )
    parser.add_argument(
        "paths", nargs="+", help="Files or directories to normalize"
    )
    args = parser.parse_args()

    changed = 0
    for p_str in args.paths:
        p = Path(p_str)
        if p.is_dir():
            for md_file in p.rglob("*.md"):
                if process_file(md_file):
                    changed += 1
        elif p.is_file() and p.suffix.lower() == ".md":
            if process_file(p):
                changed += 1

    print(f"Normalized files: {changed}")


if __name__ == "__main__":
    main()
