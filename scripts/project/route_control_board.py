#!/usr/bin/env python3
"""Event-driven auto-routing for CDB Control Board project items."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


STAGE_LABEL_TO_OPTION: tuple[tuple[str, str], ...] = (
    ("label:stage:proof", "proof"),
    ("label:stage:stability", "stability"),
    ("label:stage:trade-capable", "trade-capable"),
    ("label:stage:strategy-validated", "strategy-validated"),
    # Backward-compatible aliases in case legacy labels still exist.
    ("stage:proof", "proof"),
    ("stage:stability", "stability"),
    ("stage:trade-capable", "trade-capable"),
    ("stage:strategy-validated", "strategy-validated"),
)

STAGE_TO_MILESTONE: dict[str, str] = {
    "proof": "System ist beweisbar",
    "stability": "System ist stabil",
    "trade-capable": "System kann handeln",
    "strategy-validated": "Strategie ist validiert",
}
AUTOMATION_MANAGED_MILESTONES: frozenset[str] = frozenset(STAGE_TO_MILESTONE.values())

PRIORITY_LABEL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^(?:label:)?(?:prio|priority):p([0-3])$", re.IGNORECASE),
    re.compile(r"^(?:label:)?(?:prio|priority):([0-3])$", re.IGNORECASE),
    re.compile(r"^p([0-3])$", re.IGNORECASE),
)

PRIORITY_TITLE_PREFIX = re.compile(
    r"^\s*(?:\[(P[0-3])\]|(P[0-3]))(?:\b|[\s:|\]-])",
    re.IGNORECASE,
)


class GhCommandError(RuntimeError):
    """Raised when gh invocations fail."""


@dataclass(frozen=True)
class RouteTarget:
    kind: str
    number: int
    node_id: str
    title: str
    labels: tuple[str, ...]
    milestone_title: str
    url: str


class ControlBoardRouter:
    def __init__(
        self,
        owner: str,
        repo_name: str,
        project_number: int,
        event_name: str,
        event_path: Path,
        apply_changes: bool,
    ) -> None:
        self.owner = owner
        self.repo_name = repo_name
        self.project_number = project_number
        self.event_name = event_name
        self.event_path = event_path
        self.apply_changes = apply_changes
        self.repo_full = f"{owner}/{repo_name}"
        self.project_id = ""
        self.field_id_by_name: dict[str, str] = {}
        self.option_id_by_field_and_name: dict[tuple[str, str], str] = {}
        self.milestone_number_by_title: dict[str, int] = {}

    def log(self, message: str) -> None:
        print(message)

    def gh_json(
        self, args: list[str], payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        cmd = ["gh", *args]
        proc = subprocess.run(
            cmd,
            input=json.dumps(payload) if payload is not None else None,
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            stderr = proc.stderr.strip()
            stdout = proc.stdout.strip()
            details = stderr or stdout or f"exit-code={proc.returncode}"
            raise GhCommandError(f"{' '.join(cmd)} failed: {details}")
        out = proc.stdout.strip()
        if not out:
            return {}
        try:
            return json.loads(out)
        except json.JSONDecodeError as exc:
            raise GhCommandError(f"Invalid JSON from {' '.join(cmd)}: {exc}") from exc

    def graphql(
        self, query: str, variables: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload = {"query": query, "variables": variables or {}}
        response = self.gh_json(["api", "graphql", "--input", "-"], payload=payload)
        errors = response.get("errors") or []
        if errors:
            messages = ", ".join(
                str(err.get("message", "unknown graphql error")) for err in errors
            )
            raise GhCommandError(messages)
        return response.get("data", {})

    def rest_json(self, endpoint: str, method: str = "GET", **fields: Any) -> dict[str, Any]:
        args = ["api", endpoint]
        if method.upper() != "GET":
            args = ["api", "--method", method.upper(), endpoint]
        for key, value in fields.items():
            args.extend(["-f", f"{key}={value}"])
        return self.gh_json(args)

    def load_project_metadata(self) -> None:
        query = """
query($owner:String!,$number:Int!){
  user(login:$owner){
    projectV2(number:$number){
      id
      fields(first:100){
        nodes{
          __typename
          ... on ProjectV2Field { id name }
          ... on ProjectV2SingleSelectField {
            id
            name
            options { id name }
          }
          ... on ProjectV2IterationField { id name }
        }
      }
    }
  }
}
"""
        data = self.graphql(
            query,
            {"owner": self.owner, "number": self.project_number},
        )
        project = ((data.get("user") or {}).get("projectV2")) or None
        if not project:
            raise GhCommandError(
                f"Project not found (owner={self.owner}, number={self.project_number})"
            )
        project_id = project.get("id")
        if not project_id:
            raise GhCommandError("Project id missing.")
        self.project_id = str(project_id)

        for node in (project.get("fields") or {}).get("nodes") or []:
            name = str(node.get("name", ""))
            field_id = str(node.get("id", ""))
            if not name or not field_id:
                continue
            self.field_id_by_name[name] = field_id
            if node.get("__typename") == "ProjectV2SingleSelectField":
                for option in node.get("options") or []:
                    option_name = str(option.get("name", ""))
                    option_id = str(option.get("id", ""))
                    if option_name and option_id:
                        self.option_id_by_field_and_name[(name, option_name)] = option_id

    def load_event_payload(self) -> dict[str, Any]:
        try:
            return json.loads(self.event_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise GhCommandError(f"Event payload file not found: {self.event_path}") from exc
        except json.JSONDecodeError as exc:
            raise GhCommandError(f"Invalid event JSON: {exc}") from exc

    def parse_priority(self, title: str, labels: tuple[str, ...]) -> str | None:
        label_priorities: set[str] = set()
        for label in labels:
            for pattern in PRIORITY_LABEL_PATTERNS:
                match = pattern.match(label.strip())
                if match:
                    label_priorities.add(f"P{match.group(1)}")
                    break

        title_priority = None
        title_match = PRIORITY_TITLE_PREFIX.match(title or "")
        if title_match:
            value = title_match.group(1) or title_match.group(2)
            title_priority = value.upper() if value else None

        label_priority_list = sorted(label_priorities)
        if len(label_priority_list) > 1:
            self.log(
                "WARN: multiple priority labels found; skipping Priority update to avoid ambiguity."
            )
            return None
        if len(label_priority_list) == 1:
            label_priority = label_priority_list[0]
            if title_priority and title_priority != label_priority:
                self.log(
                    "WARN: title priority and label priority differ; using label priority."
                )
            return label_priority
        return title_priority

    def parse_stage(self, labels: tuple[str, ...]) -> tuple[str | None, bool]:
        lowered = {label.strip().casefold() for label in labels}
        matches: list[str] = []
        for stage_label, stage_option in STAGE_LABEL_TO_OPTION:
            if stage_label.casefold() in lowered and stage_option not in matches:
                matches.append(stage_option)
        if not matches:
            return None, False
        if len(matches) > 1:
            self.log(
                "WARN: multiple stage labels found; skipping Stage update to avoid ambiguity."
            )
            return None, True
        return matches[0], False

    def load_milestones(self) -> None:
        data = self.gh_json(
            [
                "api",
                "--paginate",
                "--slurp",
                f"repos/{self.repo_full}/milestones?state=all&per_page=100",
            ]
        )
        pages = data if isinstance(data, list) else []
        for page in pages:
            for milestone in page or []:
                title = str(milestone.get("title", ""))
                number = milestone.get("number")
                if title and isinstance(number, int):
                    self.milestone_number_by_title[title] = number

    def issue_target_from_api(self, number: int) -> RouteTarget:
        data = self.rest_json(f"repos/{self.repo_full}/issues/{number}")
        labels = tuple(
            label.get("name", "")
            for label in data.get("labels") or []
            if isinstance(label.get("name"), str) and label.get("name")
        )
        return RouteTarget(
            kind="Issue",
            number=int(data.get("number")),
            node_id=str(data.get("node_id", "")),
            title=str(data.get("title", "")),
            labels=labels,
            milestone_title=str(((data.get("milestone") or {}).get("title")) or ""),
            url=str(data.get("html_url", "")),
        )

    def pr_target_from_api(self, number: int) -> RouteTarget:
        data = self.rest_json(f"repos/{self.repo_full}/pulls/{number}")
        labels = tuple(
            label.get("name", "")
            for label in data.get("labels") or []
            if isinstance(label.get("name"), str) and label.get("name")
        )
        return RouteTarget(
            kind="PullRequest",
            number=int(data.get("number")),
            node_id=str(data.get("node_id", "")),
            title=str(data.get("title", "")),
            labels=labels,
            milestone_title=str(((data.get("milestone") or {}).get("title")) or ""),
            url=str(data.get("html_url", "")),
        )

    def linked_issue_numbers_for_pr(self, pr_number: int) -> list[int]:
        query = """
query($owner:String!,$repo:String!,$number:Int!){
  repository(owner:$owner,name:$repo){
    pullRequest(number:$number){
      closingIssuesReferences(first:100){
        nodes{ number }
      }
    }
  }
}
"""
        data = self.graphql(
            query,
            {
                "owner": self.owner,
                "repo": self.repo_name,
                "number": pr_number,
            },
        )
        nodes = (
            ((((data.get("repository") or {}).get("pullRequest")) or {}).get(
                "closingIssuesReferences"
            ) or {})
        ).get("nodes") or []
        result: list[int] = []
        for node in nodes:
            number = node.get("number")
            if isinstance(number, int):
                result.append(number)
        return result

    def collect_targets(self, payload: dict[str, Any]) -> list[RouteTarget]:
        targets: list[RouteTarget] = []
        if self.event_name == "issues":
            issue = payload.get("issue") or {}
            number = issue.get("number")
            if not isinstance(number, int):
                raise GhCommandError("Issue event without issue number.")
            targets.append(self.issue_target_from_api(number))
            return targets

        if self.event_name != "pull_request":
            self.log(f"No routing for event '{self.event_name}'.")
            return targets

        pr = payload.get("pull_request") or {}
        pr_number = pr.get("number")
        if not isinstance(pr_number, int):
            raise GhCommandError("Pull request event without pull_request number.")

        targets.append(self.pr_target_from_api(pr_number))

        linked_issues = self.linked_issue_numbers_for_pr(pr_number)
        for issue_number in linked_issues:
            targets.append(self.issue_target_from_api(issue_number))
        return targets

    def find_project_item_by_content_id(self, content_id: str) -> dict[str, Any] | None:
        query = """
query($owner:String!,$number:Int!,$after:String){
  user(login:$owner){
    projectV2(number:$number){
      items(first:100,after:$after){
        pageInfo{ hasNextPage endCursor }
        nodes{
          id
          content{
            __typename
            ... on Issue{
              id
              repository{ nameWithOwner }
            }
            ... on PullRequest{
              id
              repository{ nameWithOwner }
            }
          }
          status: fieldValueByName(name:"Status"){
            __typename
            ... on ProjectV2ItemFieldSingleSelectValue{
              optionId
              name
            }
          }
          stage: fieldValueByName(name:"Stage"){
            __typename
            ... on ProjectV2ItemFieldSingleSelectValue{
              optionId
              name
            }
          }
          priority: fieldValueByName(name:"Priority"){
            __typename
            ... on ProjectV2ItemFieldSingleSelectValue{
              optionId
              name
            }
          }
        }
      }
    }
  }
}
"""
        cursor: str | None = None
        page_count = 0
        while True:
            page_count += 1
            if page_count > 30:
                raise GhCommandError("Exceeded max project item pages while searching item.")
            data = self.graphql(
                query,
                {
                    "owner": self.owner,
                    "number": self.project_number,
                    "after": cursor,
                },
            )
            items = (
                (((data.get("user") or {}).get("projectV2") or {}).get("items") or {})
            )
            for node in items.get("nodes") or []:
                content = node.get("content") or {}
                if str(content.get("id", "")) != content_id:
                    continue
                if str(((content.get("repository") or {}).get("nameWithOwner")) or "") != self.repo_full:
                    continue
                return node

            page = items.get("pageInfo") or {}
            if not page.get("hasNextPage"):
                return None
            cursor = page.get("endCursor")
            if not cursor:
                return None

    def add_item_to_project(self, content_id: str) -> str | None:
        mutation = """
mutation($projectId:ID!,$contentId:ID!){
  addProjectV2ItemById(input:{projectId:$projectId,contentId:$contentId}){
    item{ id }
  }
}
"""
        if not self.apply_changes:
            self.log(f"DRY-RUN: would add content '{content_id}' to project")
            return None

        payload = {
            "query": mutation,
            "variables": {"projectId": self.project_id, "contentId": content_id},
        }
        response = self.gh_json(["api", "graphql", "--input", "-"], payload=payload)
        errors = response.get("errors") or []
        if errors:
            messages = [str(err.get("message", "")) for err in errors]
            normalized = " | ".join(messages).lower()
            if "already exists" in normalized:
                return "__ALREADY_EXISTS__"
            raise GhCommandError("; ".join(messages))
        item = ((response.get("data") or {}).get("addProjectV2ItemById") or {}).get(
            "item"
        ) or {}
        item_id = item.get("id")
        return str(item_id) if item_id else None

    def ensure_project_item(self, content_id: str) -> dict[str, Any]:
        existing = self.find_project_item_by_content_id(content_id)
        if existing:
            return existing

        if not self.apply_changes:
            self.log(f"DRY-RUN: content '{content_id}' is not yet in project")
            return {
                "id": f"dryrun:{content_id}",
                "status": {"name": "", "optionId": ""},
                "stage": {"name": "", "optionId": ""},
                "priority": {"name": "", "optionId": ""},
            }

        added = self.add_item_to_project(content_id)
        if added and added != "__ALREADY_EXISTS__":
            self.log(f"APPLY: added content '{content_id}' to project")
            return {
                "id": added,
                "status": {"name": "", "optionId": ""},
                "stage": {"name": "", "optionId": ""},
                "priority": {"name": "", "optionId": ""},
            }

        lookup = self.find_project_item_by_content_id(content_id)
        if lookup:
            return lookup
        raise GhCommandError(f"Project item lookup failed for content id {content_id}.")

    def set_single_select(
        self,
        item_id: str,
        field_name: str,
        option_name: str,
        current_option_id: str,
    ) -> None:
        field_id = self.field_id_by_name.get(field_name)
        option_id = self.option_id_by_field_and_name.get((field_name, option_name))
        if not field_id or not option_id:
            self.log(
                f"SKIP: field '{field_name}' or option '{option_name}' not available in project."
            )
            return
        if option_id == current_option_id:
            return
        if not self.apply_changes:
            self.log(
                f"DRY-RUN: would set {field_name}='{option_name}' on project item '{item_id}'"
            )
            return

        mutation = """
mutation($projectId:ID!,$itemId:ID!,$fieldId:ID!,$optionId:String!){
  updateProjectV2ItemFieldValue(input:{
    projectId:$projectId,
    itemId:$itemId,
    fieldId:$fieldId,
    value:{singleSelectOptionId:$optionId}
  }){
    projectV2Item{ id }
  }
}
"""
        self.graphql(
            mutation,
            {
                "projectId": self.project_id,
                "itemId": item_id,
                "fieldId": field_id,
                "optionId": option_id,
            },
        )
        self.log(f"APPLY: set {field_name}='{option_name}' for item '{item_id}'")

    def clear_field_if_set(
        self,
        item_id: str,
        field_name: str,
        current_option_id: str,
    ) -> None:
        field_id = self.field_id_by_name.get(field_name)
        if not field_id:
            return
        if not current_option_id:
            return
        if not self.apply_changes:
            self.log(f"DRY-RUN: would clear field '{field_name}' on item '{item_id}'")
            return
        mutation = """
mutation($projectId:ID!,$itemId:ID!,$fieldId:ID!){
  clearProjectV2ItemFieldValue(input:{
    projectId:$projectId,
    itemId:$itemId,
    fieldId:$fieldId
  }){
    projectV2Item{ id }
  }
}
"""
        self.graphql(
            mutation,
            {
                "projectId": self.project_id,
                "itemId": item_id,
                "fieldId": field_id,
            },
        )
        self.log(f"APPLY: cleared field '{field_name}' for item '{item_id}'")

    def ensure_issue_milestone(
        self, issue_number: int, current_title: str, desired_title: str
    ) -> None:
        if not desired_title:
            return
        if current_title == desired_title:
            return
        if current_title and current_title not in AUTOMATION_MANAGED_MILESTONES:
            self.log(
                "SKIP: current milestone is not managed by automation; milestone update skipped."
            )
            return
        milestone_number = self.milestone_number_by_title.get(desired_title)
        if milestone_number is None:
            self.log(f"SKIP: milestone '{desired_title}' not found in repo.")
            return
        if not self.apply_changes:
            self.log(
                f"DRY-RUN: would set milestone '{desired_title}' on issue #{issue_number}"
            )
            return
        self.rest_json(
            f"repos/{self.repo_full}/issues/{issue_number}",
            method="PATCH",
            milestone=milestone_number,
        )
        self.log(f"APPLY: set milestone '{desired_title}' on issue #{issue_number}")

    def route_issue(self, target: RouteTarget, item: dict[str, Any]) -> None:
        stage_option, stage_conflict = self.parse_stage(target.labels)
        priority_option = self.parse_priority(target.title, target.labels)
        desired_milestone = ""
        if not stage_conflict:
            desired_milestone = STAGE_TO_MILESTONE.get(stage_option or "", "")

        item_id = str(item.get("id", ""))
        status_current_option = str(((item.get("status") or {}).get("optionId")) or "")
        stage_current_option = str(((item.get("stage") or {}).get("optionId")) or "")
        priority_current_option = str(
            ((item.get("priority") or {}).get("optionId")) or ""
        )

        if not status_current_option:
            self.set_single_select(item_id, "Status", "Backlog", status_current_option)

        if stage_conflict:
            self.log("WARN: Stage conflict detected; keeping existing Stage value.")
        elif stage_option:
            self.set_single_select(item_id, "Stage", stage_option, stage_current_option)
        else:
            self.clear_field_if_set(item_id, "Stage", stage_current_option)

        if priority_option:
            self.set_single_select(
                item_id,
                "Priority",
                priority_option,
                priority_current_option,
            )

        self.ensure_issue_milestone(
            issue_number=target.number,
            current_title=target.milestone_title,
            desired_title=desired_milestone,
        )

    def route_pr(self, target: RouteTarget, item: dict[str, Any]) -> None:
        item_id = str(item.get("id", ""))
        if not item_id:
            return
        status_current_option = str(((item.get("status") or {}).get("optionId")) or "")
        stage_current_option = str(((item.get("stage") or {}).get("optionId")) or "")
        priority_current_option = str(
            ((item.get("priority") or {}).get("optionId")) or ""
        )

        if not status_current_option:
            self.set_single_select(item_id, "Status", "Backlog", status_current_option)

        stage_option, stage_conflict = self.parse_stage(target.labels)
        if stage_conflict:
            self.log("WARN: Stage conflict detected; keeping existing Stage value.")
        elif stage_option:
            self.set_single_select(item_id, "Stage", stage_option, stage_current_option)
        else:
            self.clear_field_if_set(item_id, "Stage", stage_current_option)

        priority_option = self.parse_priority(target.title, target.labels)
        if priority_option:
            self.set_single_select(
                item_id,
                "Priority",
                priority_option,
                priority_current_option,
            )

        self.log(f"INFO: PR item '{item_id}' routed.")

    def run(self) -> int:
        self.log(
            f"Control Board routing start (repo={self.repo_full}, project={self.owner}/"
            f"{self.project_number}, mode={'APPLY' if self.apply_changes else 'DRY-RUN'})"
        )
        payload = self.load_event_payload()
        self.load_project_metadata()
        self.load_milestones()
        targets = self.collect_targets(payload)
        if not targets:
            self.log("No route targets for this event.")
            return 0

        for target in targets:
            if not target.node_id:
                self.log(
                    f"SKIP: {target.kind} #{target.number} has no node id and cannot be routed."
                )
                continue

            item = self.ensure_project_item(target.node_id)
            if target.kind == "Issue":
                self.route_issue(target, item)
            elif target.kind == "PullRequest":
                self.route_pr(target, item)

        self.log("Control Board routing complete.")
        return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Auto-route issue/PR events into CDB Control Board fields."
    )
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", ""))
    parser.add_argument("--owner", default=os.getenv("PROJECT_OWNER"))
    parser.add_argument(
        "--project-number",
        type=int,
        default=int(os.getenv("PROJECT_NUMBER", "0") or 0),
    )
    parser.add_argument("--event-name", default=os.getenv("GITHUB_EVENT_NAME", ""))
    parser.add_argument("--event-path", default=os.getenv("GITHUB_EVENT_PATH", ""))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Preview only.")
    mode.add_argument("--apply", action="store_true", help="Apply mutations.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.owner:
        print("Missing --owner (or PROJECT_OWNER).", file=sys.stderr)
        return 2
    if not args.project_number:
        print("Missing --project-number (or PROJECT_NUMBER).", file=sys.stderr)
        return 2
    if not args.repo or "/" not in args.repo:
        print("Missing --repo in '<owner>/<repo>' format.", file=sys.stderr)
        return 2
    if not args.event_name:
        print("Missing --event-name (or GITHUB_EVENT_NAME).", file=sys.stderr)
        return 2
    if not args.event_path:
        print("Missing --event-path (or GITHUB_EVENT_PATH).", file=sys.stderr)
        return 2

    repo_owner, repo_name = args.repo.split("/", maxsplit=1)
    if repo_owner.casefold() != args.owner.casefold():
        print(
            f"Owner mismatch: --owner '{args.owner}' != repo owner '{repo_owner}'.",
            file=sys.stderr,
        )
        return 2

    router = ControlBoardRouter(
        owner=args.owner,
        repo_name=repo_name,
        project_number=args.project_number,
        event_name=args.event_name,
        event_path=Path(args.event_path),
        apply_changes=bool(args.apply),
    )
    try:
        return router.run()
    except GhCommandError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
