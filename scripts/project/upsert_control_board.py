#!/usr/bin/env python3
"""Idempotent upsert for CDB Control Board project fields and view columns."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OptionSpec:
    name: str
    color: str = "GRAY"
    description: str = ""


@dataclass(frozen=True)
class FieldSpec:
    name: str
    data_type: str
    options: tuple[OptionSpec, ...] = ()
    optional: bool = False


class GhCommandError(RuntimeError):
    """Raised when gh invocations fail."""


REQUIRED_FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec(
        name="Priority",
        data_type="SINGLE_SELECT",
        options=(
            OptionSpec("P0", color="RED"),
            OptionSpec("P1", color="ORANGE"),
            OptionSpec("P2", color="YELLOW"),
            OptionSpec("P3", color="BLUE"),
        ),
    ),
    FieldSpec(
        name="Stage",
        data_type="SINGLE_SELECT",
        options=(
            OptionSpec("proof", color="BLUE"),
            OptionSpec("stability", color="YELLOW"),
            OptionSpec("trade-capable", color="ORANGE"),
            OptionSpec("strategy-validated", color="GREEN"),
        ),
    ),
    FieldSpec(name="Evidence", data_type="TEXT"),
    FieldSpec(
        name="Blocked",
        data_type="SINGLE_SELECT",
        options=(
            OptionSpec("No", color="GREEN"),
            OptionSpec("Yes", color="RED"),
        ),
    ),
    FieldSpec(name="Blocker Link", data_type="TEXT"),
)

OPTIONAL_FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec(
        name="Effort",
        data_type="SINGLE_SELECT",
        options=(
            OptionSpec("S", color="GREEN"),
            OptionSpec("M", color="YELLOW"),
            OptionSpec("L", color="ORANGE"),
        ),
        optional=True,
    ),
)

TARGET_VIEWS: tuple[str, ...] = (
    "BEWEISBARKEIT",
    "STABILITÄT",
    "EINSATZFÄHIG",
    "VALIDIERUNG",
)


class ProjectUpserter:
    def __init__(self, owner: str, project_number: int, apply_changes: bool):
        self.owner = owner
        self.project_number = project_number
        self.apply_changes = apply_changes
        self.changed = False
        self.warnings: list[str] = []
        self.errors: list[str] = []

    def log(self, message: str) -> None:
        print(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)
        self.log(f"WARN: {message}")

    def error(self, message: str) -> None:
        self.errors.append(message)
        self.log(f"ERROR: {message}")

    def gh_json(self, args: list[str], payload: dict[str, Any] | None = None) -> dict[str, Any]:
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

    def load_project(self) -> dict[str, Any]:
        query = """
query($owner:String!,$number:Int!){
  user(login:$owner){
    projectV2(number:$number){
      id
      title
      fields(first:100){
        nodes{
          __typename
          ... on ProjectV2Field { id name }
          ... on ProjectV2SingleSelectField {
            id
            name
            options { id name color description }
          }
          ... on ProjectV2IterationField { id name }
        }
      }
      views(first:50){
        nodes{
          id
          name
        }
      }
    }
  }
}
"""
        data = self.graphql(
            query,
            {
                "owner": self.owner,
                "number": self.project_number,
            },
        )
        project = ((data.get("user") or {}).get("projectV2")) or None
        if not project:
            raise GhCommandError(
                f"Project not found (owner={self.owner}, number={self.project_number})"
            )
        return project

    def classify_field(self, field: dict[str, Any]) -> str:
        typename = field.get("__typename")
        if typename == "ProjectV2SingleSelectField":
            return "SINGLE_SELECT"
        if typename == "ProjectV2IterationField":
            return "ITERATION"
        return "TEXT"

    def find_field(
        self, fields: list[dict[str, Any]], name: str
    ) -> dict[str, Any] | None:
        needle = name.casefold()
        for field in fields:
            if str(field.get("name", "")).casefold() == needle:
                return field
        return None

    def create_field(self, project_id: str, spec: FieldSpec) -> dict[str, Any] | None:
        if not self.apply_changes:
            self.log(
                f"DRY-RUN: would create field '{spec.name}' ({spec.data_type})"
            )
            return None

        mutation = """
mutation($input:CreateProjectV2FieldInput!){
  createProjectV2Field(input:$input){
    projectV2Field{
      __typename
      ... on ProjectV2Field { id name }
      ... on ProjectV2SingleSelectField {
        id
        name
        options { id name color description }
      }
      ... on ProjectV2IterationField { id name }
    }
  }
}
"""
        input_payload: dict[str, Any] = {
            "projectId": project_id,
            "name": spec.name,
            "dataType": spec.data_type,
        }
        if spec.data_type == "SINGLE_SELECT":
            input_payload["singleSelectOptions"] = [
                {
                    "name": opt.name,
                    "color": opt.color,
                    "description": opt.description,
                }
                for opt in spec.options
            ]
        data = self.graphql(mutation, {"input": input_payload})
        self.changed = True
        created = (
            ((data.get("createProjectV2Field") or {}).get("projectV2Field")) or None
        )
        self.log(f"APPLY: created field '{spec.name}'")
        return created

    def update_single_select_options(
        self,
        project_id: str,
        field: dict[str, Any],
        missing_options: list[OptionSpec],
    ) -> dict[str, Any] | None:
        current_options = field.get("options") or []
        merged_options: list[dict[str, str]] = []

        for option in current_options:
            merged_options.append(
                {
                    "name": option.get("name", ""),
                    "color": option.get("color") or "GRAY",
                    "description": option.get("description") or "",
                }
            )
        for option in missing_options:
            merged_options.append(
                {
                    "name": option.name,
                    "color": option.color,
                    "description": option.description,
                }
            )

        if not self.apply_changes:
            names = ", ".join(opt.name for opt in missing_options)
            self.log(
                f"DRY-RUN: would append options [{names}] to field '{field.get('name')}'"
            )
            return None

        mutation = """
mutation($input:UpdateProjectV2FieldInput!){
  updateProjectV2Field(input:$input){
    projectV2Field{
      __typename
      ... on ProjectV2Field { id name }
      ... on ProjectV2SingleSelectField {
        id
        name
        options { id name color description }
      }
      ... on ProjectV2IterationField { id name }
    }
  }
}
"""
        input_payload = {
            "projectId": project_id,
            "fieldId": field.get("id"),
            "name": field.get("name"),
            "singleSelectOptions": merged_options,
        }
        data = self.graphql(mutation, {"input": input_payload})
        self.changed = True
        updated = (
            ((data.get("updateProjectV2Field") or {}).get("projectV2Field")) or None
        )
        names = ", ".join(opt.name for opt in missing_options)
        self.log(f"APPLY: appended options [{names}] to field '{field.get('name')}'")
        return updated

    def ensure_field(
        self, project_id: str, fields: list[dict[str, Any]], spec: FieldSpec
    ) -> None:
        existing = self.find_field(fields, spec.name)
        if existing is None:
            created = self.create_field(project_id, spec)
            if created is not None:
                fields.append(created)
            return

        current_type = self.classify_field(existing)
        if spec.data_type == "SINGLE_SELECT" and current_type != "SINGLE_SELECT":
            self.error(
                f"Field '{spec.name}' exists but is '{current_type}', expected SINGLE_SELECT."
            )
            return
        if spec.data_type == "TEXT" and current_type in {"SINGLE_SELECT", "ITERATION"}:
            self.error(
                f"Field '{spec.name}' exists but is '{current_type}', expected TEXT."
            )
            return

        if spec.data_type != "SINGLE_SELECT":
            self.log(f"OK: field '{spec.name}' already present")
            return

        current_names = {
            str(option.get("name", "")).casefold() for option in existing.get("options") or []
        }
        missing = [opt for opt in spec.options if opt.name.casefold() not in current_names]
        if not missing:
            self.log(f"OK: field '{spec.name}' already has required options")
            return
        updated = self.update_single_select_options(project_id, existing, missing)
        if updated is not None:
            existing.update(updated)

    def inspect_update_view_input(self) -> tuple[bool, str | None, str | None]:
        mutation_query = """
query {
  __type(name:"Mutation"){
    fields{ name }
  }
}
"""
        data = self.graphql(mutation_query)
        mutation_names = {
            field.get("name", "")
            for field in ((data.get("__type") or {}).get("fields") or [])
        }
        if "updateProjectV2View" not in mutation_names:
            return False, None, None

        input_query = """
query {
  __type(name:"UpdateProjectV2ViewInput"){
    inputFields{ name }
  }
}
"""
        data = self.graphql(input_query)
        input_fields = {
            field.get("name", "")
            for field in ((data.get("__type") or {}).get("inputFields") or [])
        }
        visible_key = None
        for candidate in ("visibleFieldIds", "fieldIds"):
            if candidate in input_fields:
                visible_key = candidate
                break
        view_id_key = None
        for candidate in ("viewId", "id"):
            if candidate in input_fields:
                view_id_key = candidate
                break
        if visible_key is None or view_id_key is None:
            return True, None, None
        return True, visible_key, view_id_key

    def load_view_visible_field_ids(self) -> dict[str, list[str]]:
        query = """
query($owner:String!,$number:Int!){
  user(login:$owner){
    projectV2(number:$number){
      views(first:50){
        nodes{
          id
          name
          visibleFields(first:100){
            nodes{
              __typename
              ... on ProjectV2Field { id name }
              ... on ProjectV2SingleSelectField { id name }
              ... on ProjectV2IterationField { id name }
            }
          }
        }
      }
    }
  }
}
"""
        data = self.graphql(
            query,
            {
                "owner": self.owner,
                "number": self.project_number,
            },
        )
        nodes = (
            (((data.get("user") or {}).get("projectV2") or {}).get("views") or {})
            .get("nodes")
            or []
        )
        result: dict[str, list[str]] = {}
        for view in nodes:
            ids: list[str] = []
            for field in ((view.get("visibleFields") or {}).get("nodes") or []):
                field_id = field.get("id")
                if field_id:
                    ids.append(field_id)
            view_name = str(view.get("name", ""))
            if view_name:
                result[view_name] = ids
        return result

    def update_view_columns(
        self,
        view_id: str,
        project_id: str,
        visible_key: str,
        view_id_key: str,
        desired_field_ids: list[str],
    ) -> None:
        if not self.apply_changes:
            self.log(
                f"DRY-RUN: would update view '{view_id}' with {len(desired_field_ids)} visible fields"
            )
            return

        input_payload: dict[str, Any] = {
            visible_key: desired_field_ids,
            view_id_key: view_id,
        }
        # Some GitHub schema versions include projectId in this input.
        input_payload["projectId"] = project_id

        mutation = """
mutation($input:UpdateProjectV2ViewInput!){
  updateProjectV2View(input:$input){
    projectV2View{ id name }
  }
}
"""
        try:
            self.graphql(mutation, {"input": input_payload})
        except GhCommandError:
            # Retry without projectId for schemas that don't allow it.
            input_payload.pop("projectId", None)
            self.graphql(mutation, {"input": input_payload})

        self.changed = True

    def ensure_view_columns(
        self,
        project: dict[str, Any],
        fields: list[dict[str, Any]],
    ) -> None:
        supports_mutation, visible_key, view_id_key = self.inspect_update_view_input()
        if not supports_mutation:
            self.warn(
                "updateProjectV2View mutation not available; skipped automatic view-column sync."
            )
            return
        if visible_key is None or view_id_key is None:
            self.warn(
                "updateProjectV2View exists but required input keys were not discoverable; skipped view-column sync."
            )
            return

        field_by_name = {
            str(field.get("name", "")).casefold(): field for field in fields if field.get("name")
        }

        def id_for(candidates: tuple[str, ...]) -> str | None:
            for name in candidates:
                candidate = field_by_name.get(name.casefold())
                if candidate and candidate.get("id"):
                    return str(candidate["id"])
            return None

        required_field_ids: list[str] = []
        required_lookup = {
            "Priority": ("Priority",),
            "Stage": ("Stage",),
            "Owner/Assignees": ("Assignees", "Owner"),
            "Evidence": ("Evidence",),
            "Linked PRs": ("Linked pull requests", "Linked PRs", "Linked Pull Requests"),
            "Milestone": ("Milestone",),
        }
        for label, names in required_lookup.items():
            field_id = id_for(names)
            if not field_id:
                self.warn(f"Could not resolve field id for '{label}' while syncing views.")
                continue
            required_field_ids.append(field_id)

        if not required_field_ids:
            self.warn("No required field ids resolved; skipped view-column sync.")
            return

        visible_fields_by_view = self.load_view_visible_field_ids()

        views = ((project.get("views") or {}).get("nodes")) or []
        for view in views:
            view_name = str(view.get("name", ""))
            if view_name not in TARGET_VIEWS:
                continue
            view_id = str(view.get("id", ""))
            if not view_id:
                self.warn(f"View '{view_name}' has no id; skipped.")
                continue

            current_visible = visible_fields_by_view.get(view_name, [])
            merged = list(dict.fromkeys([*current_visible, *required_field_ids]))
            if merged == current_visible:
                self.log(f"OK: view '{view_name}' already exposes required columns")
                continue

            self.update_view_columns(
                view_id=view_id,
                project_id=str(project.get("id", "")),
                visible_key=visible_key,
                view_id_key=view_id_key,
                desired_field_ids=merged,
            )
            self.log(f"APPLY: synced visible columns for view '{view_name}'")

        existing_view_names = {str(view.get("name", "")) for view in views}
        for required_view in TARGET_VIEWS:
            if required_view not in existing_view_names:
                self.warn(f"Expected view '{required_view}' was not found in project.")

    def run(self, include_effort: bool, sync_view_columns: bool) -> int:
        self.log(
            f"Project upsert start (owner={self.owner}, number={self.project_number}, "
            f"mode={'APPLY' if self.apply_changes else 'DRY-RUN'})"
        )
        project = self.load_project()
        project_id = str(project.get("id", ""))
        if not project_id:
            raise GhCommandError("Project ID is missing.")

        fields = list(((project.get("fields") or {}).get("nodes")) or [])
        specs = [*REQUIRED_FIELDS]
        if include_effort:
            specs.extend(OPTIONAL_FIELDS)
        for spec in specs:
            self.ensure_field(project_id, fields, spec)

        if sync_view_columns:
            self.ensure_view_columns(project, fields)

        self.log("Project upsert complete.")
        if self.errors:
            self.log(f"FAILED with {len(self.errors)} error(s).")
            return 2
        if self.warnings:
            self.log(f"Completed with {len(self.warnings)} warning(s).")
        return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Idempotent upsert for CDB Control Board project fields/views."
    )
    parser.add_argument("--owner", default=os.getenv("PROJECT_OWNER"))
    parser.add_argument(
        "--project-number",
        type=int,
        default=int(os.getenv("PROJECT_NUMBER", "0") or 0),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Preview only (default).")
    mode.add_argument("--apply", action="store_true", help="Apply mutations.")
    parser.add_argument(
        "--skip-effort",
        action="store_true",
        help="Do not enforce optional Effort field.",
    )
    parser.add_argument(
        "--skip-view-columns",
        action="store_true",
        help="Skip view visible-column synchronization.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.owner:
        print("Missing --owner (or PROJECT_OWNER env).", file=sys.stderr)
        return 2
    if not args.project_number:
        print("Missing --project-number (or PROJECT_NUMBER env).", file=sys.stderr)
        return 2

    apply_changes = bool(args.apply)
    upserter = ProjectUpserter(
        owner=args.owner,
        project_number=args.project_number,
        apply_changes=apply_changes,
    )
    try:
        return upserter.run(
            include_effort=not args.skip_effort,
            sync_view_columns=not args.skip_view_columns,
        )
    except GhCommandError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
