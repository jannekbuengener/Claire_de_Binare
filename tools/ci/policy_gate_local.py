"""Local mirror of `.github/workflows/policy-gate.yml` evaluation rules.

Pure, fail-closed evaluation used by the local status publisher before writing
the required-path App Check Run ``cdb-local-ci`` (``app_id=4410232``).
Does not call GitHub.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from typing import Mapping, Sequence

WORKFLOW_SCOPE_COMPANION_DOC_PATHS: tuple[str, ...] = (
    "docs/runbooks/project_board_automation.md",
    "docs/runbooks/merge_policy_ci_gate.md",
    "docs/runbooks/CONTROL_REGISTER.md",
)
_WORKFLOW_SCOPE_COMPANION_DOCS = frozenset(WORKFLOW_SCOPE_COMPANION_DOC_PATHS)
_WORKFLOW_SCOPE_COMPANION_DOCS_LIST = ", ".join(WORKFLOW_SCOPE_COMPANION_DOC_PATHS)
_WORKFLOW_PATH_DESCRIPTION = ".github/workflows/*.yml and .github/workflows/*.yaml"
_EXPLICIT_PERMISSIONS_PATTERN = re.compile(r"^(?!\s*#)\s*permissions\s*:", re.MULTILINE)


@dataclass(frozen=True)
class PolicyGateResult:
    """Outcome of a local policy-gate evaluation."""

    ok: bool
    category: str
    category_source: str
    failures: list[str] = field(default_factory=list)
    passes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _is_docs_file(path: str) -> bool:
    return path.startswith("docs/") or path.lower().endswith(".md")


def _is_workflow_file(path: str) -> bool:
    return path.startswith(".github/workflows/") and (
        path.endswith(".yml") or path.endswith(".yaml")
    )


def _is_workflow_scope_companion_doc(path: str) -> bool:
    return path in _WORKFLOW_SCOPE_COMPANION_DOCS


def _is_infra_file(path: str) -> bool:
    return path.startswith("infrastructure/")


def _has_label(label_set: set[str], name: str) -> bool:
    return name in label_set


def _has_prefix(title_lower: str, name: str) -> bool:
    return title_lower.startswith(f"[{name}]") or title_lower.startswith(f"{name}:")


def _has_checkout_behavior(content: str) -> bool:
    # Mirror policy-gate.yml detectors, plus the common YAML list form
    # ``- uses: actions/checkout@`` / ``- name: ...checkout...``.
    return bool(
        re.search(
            r"^(?!\s*#)\s*-?\s*uses:\s*actions/checkout@",
            content,
            re.MULTILINE | re.IGNORECASE,
        )
        or re.search(
            r"^(?!\s*#)\s*-?\s*name:\s*.*checkout.*$",
            content,
            re.MULTILINE | re.IGNORECASE,
        )
        or re.search(r"\bgit\s+checkout\b", content, re.IGNORECASE)
    )


def _normalize_files(
    files: Sequence[Mapping[str, object]],
) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for entry in files:
        filename = str(entry.get("filename") or "").strip()
        if not filename:
            continue
        status = str(entry.get("status") or "modified").strip() or "modified"
        normalized.append({"filename": filename, "status": status})
    return normalized


def evaluate_policy_gate(
    *,
    title: str,
    labels: Sequence[str],
    files: Sequence[Mapping[str, object]],
    workflow_contents: Mapping[str, str] | None = None,
) -> PolicyGateResult:
    """Evaluate PR category, scope, and workflow safety (policy-gate mirror).

    Parameters
    ----------
    title:
        Pull request title.
    labels:
        Label names on the PR.
    files:
        Changed files as mappings with at least ``filename`` and optional
        ``status`` (``removed`` skips workflow content inspection).
    workflow_contents:
        Optional map of workflow path -> file text at PR head. Required for
        non-removed workflow files; missing content yields a failure.
    """
    label_list = [str(label) for label in labels]
    label_set = {label.lower() for label in label_list}
    title_text = (title or "").strip()
    title_lower = title_text.lower()
    normalized = _normalize_files(files)
    changed_files = [item["filename"] for item in normalized]
    contents = dict(workflow_contents or {})

    category = "core/service"
    category_source = "default"

    if _has_label(label_set, "docs-only") or _has_prefix(title_lower, "docs-only"):
        category = "docs-only"
        category_source = (
            "label:docs-only" if _has_label(label_set, "docs-only") else "title-prefix"
        )
    elif _has_label(label_set, "workflows-only") or _has_prefix(
        title_lower, "workflows-only"
    ):
        category = "workflows-only"
        category_source = (
            "label:workflows-only"
            if _has_label(label_set, "workflows-only")
            else "title-prefix"
        )
    elif _has_label(label_set, "infra-only") or _has_prefix(title_lower, "infra-only"):
        category = "infra-only"
        category_source = (
            "label:infra-only"
            if _has_label(label_set, "infra-only")
            else "title-prefix"
        )
    elif changed_files and all(_is_docs_file(path) for path in changed_files):
        category = "docs-only"
        category_source = "file-inference"
    elif changed_files and all(
        _is_workflow_file(path) or _is_workflow_scope_companion_doc(path)
        for path in changed_files
    ):
        category = "workflows-only"
        category_source = "file-inference"
    elif changed_files and all(_is_infra_file(path) for path in changed_files):
        category = "infra-only"
        category_source = "file-inference"

    failures: list[str] = []
    passes: list[str] = []

    if category == "docs-only":
        invalid_docs = [path for path in changed_files if not _is_docs_file(path)]
        if invalid_docs:
            failures.append(
                "docs-only allows only docs/** and *.md, but found: "
                + ", ".join(invalid_docs)
            )
        else:
            passes.append("docs-only scope validated")
    elif category == "workflows-only":
        invalid_workflow = [
            path
            for path in changed_files
            if not _is_workflow_file(path)
            and not _is_workflow_scope_companion_doc(path)
        ]
        if invalid_workflow:
            failures.append(
                "workflows-only allows only "
                f"{_WORKFLOW_PATH_DESCRIPTION} plus the fixed companion docs "
                f"{_WORKFLOW_SCOPE_COMPANION_DOCS_LIST}, but found: "
                + ", ".join(invalid_workflow)
            )
        else:
            passes.append("workflows-only scope validated")
    elif category == "infra-only":
        invalid_infra = [
            path
            for path in changed_files
            if not _is_infra_file(path) and not _is_workflow_file(path)
        ]
        if invalid_infra:
            failures.append(
                "infra-only allows only infrastructure/** and .github/workflows/**, "
                "but found: " + ", ".join(invalid_infra)
            )
        else:
            passes.append("infra-only scope validated")
    else:
        passes.append("core/service scope classified; no manual label required")

    workflow_files = [
        item
        for item in normalized
        if _is_workflow_file(item["filename"]) and item["status"] != "removed"
    ]

    for item in workflow_files:
        path = item["filename"]
        if path not in contents:
            failures.append(f"Unable to inspect workflow file: {path}")
            continue
        content = contents[path]

        if re.search(r"^\s*pull_request_target\s*:", content, re.MULTILINE):
            failures.append(f"Workflow {path} contains pull_request_target")

        if re.search(r"^\s*workflow_run\s*:", content, re.MULTILINE):
            if _has_checkout_behavior(content):
                failures.append(
                    f"Workflow {path} is triggered by workflow_run and must remain "
                    "metadata-only (no checkout behavior)"
                )
            else:
                passes.append(f"workflow_run metadata-only validated for {path}")

        if not _EXPLICIT_PERMISSIONS_PATTERN.search(content):
            failures.append(
                f"Workflow {path} is missing an explicit permissions section"
            )

        if re.search(r"^\s*permissions\s*:\s*write-all\s*$", content, re.MULTILINE):
            failures.append(f"Workflow {path} contains write-all")

    return PolicyGateResult(
        ok=len(failures) == 0,
        category=category,
        category_source=category_source,
        failures=failures,
        passes=passes,
    )


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools.ci.policy_gate_local",
        description="Evaluate local policy-gate rules against a JSON description.",
    )
    parser.add_argument(
        "--input",
        required=True,
        help=(
            "JSON file with keys title, labels, files "
            "[{filename,status}], optional workflow_contents {path:text}"
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_cli_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    with open(args.input, encoding="utf-8") as handle:
        payload = json.load(handle)
    result = evaluate_policy_gate(
        title=str(payload.get("title") or ""),
        labels=list(payload.get("labels") or []),
        files=list(payload.get("files") or []),
        workflow_contents=payload.get("workflow_contents") or {},
    )
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
