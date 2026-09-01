"""GitHub comment provenance transport for acceptance evidence (#4505)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CommentRecord:
    """Full comment provenance; never trust envelope producer without this."""

    comment_id: int | None
    body: str
    author_login: str | None = None
    author_type: str | None = None
    author_association: str | None = None
    performed_via_github_app_slug: str | None = None
    performed_via_github_app_id: int | None = None

    @classmethod
    def from_github_issue_comment(cls, item: dict[str, Any]) -> CommentRecord:
        user = item.get("user") if isinstance(item.get("user"), dict) else {}
        app = (
            item.get("performed_via_github_app")
            if isinstance(item.get("performed_via_github_app"), dict)
            else {}
        )
        return cls(
            comment_id=item.get("id") if isinstance(item.get("id"), int) else None,
            body=str(item.get("body") or ""),
            author_login=(
                user.get("login") if isinstance(user.get("login"), str) else None
            ),
            author_type=user.get("type") if isinstance(user.get("type"), str) else None,
            author_association=(
                item.get("author_association")
                if isinstance(item.get("author_association"), str)
                else None
            ),
            performed_via_github_app_slug=(
                app.get("slug") if isinstance(app.get("slug"), str) else None
            ),
            performed_via_github_app_id=(
                app.get("id") if isinstance(app.get("id"), int) else None
            ),
        )
