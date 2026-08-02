"""Atomic JSONL pilot store for cdb.agent_run_evidence.v1."""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from tools.agent_control.errors import EvidenceError
from tools.agent_control.evidence.codes import (
    REASON_ID_COLLISION,
    REASON_LOCK_CONFLICT,
    REASON_MALFORMED_STORE,
    REASON_TRUNCATED_LINE,
)
from tools.agent_execution_contract.jcs import canonicalize


class EvidenceJsonlStore:
    """Single-writer JSONL store. No lock stealing. Atomic append via rewrite."""

    def __init__(self, path: Path, *, lock_timeout_s: float = 5.0) -> None:
        self.path = Path(path)
        self.lock_path = Path(str(self.path) + ".lock")
        self.lock_timeout_s = lock_timeout_s

    def _acquire_lock(self) -> int:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self.lock_timeout_s
        while True:
            try:
                fd = os.open(
                    self.lock_path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o644,
                )
                os.write(fd, str(os.getpid()).encode("utf-8"))
                return fd
            except FileExistsError as exc:
                if time.monotonic() >= deadline:
                    raise EvidenceError(
                        REASON_LOCK_CONFLICT,
                        f"store lock held: {self.lock_path}",
                    ) from exc
                time.sleep(0.05)

    def _release_lock(self, fd: int) -> None:
        try:
            os.close(fd)
        finally:
            try:
                self.lock_path.unlink(missing_ok=True)
            except OSError:
                pass

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        text = self.path.read_text(encoding="utf-8")
        if not text:
            return []
        if not text.endswith("\n") and text.strip():
            raise EvidenceError(
                REASON_TRUNCATED_LINE,
                "JSONL store does not end with newline (truncated write?)",
            )
        records: list[dict[str, Any]] = []
        for line_no, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise EvidenceError(
                    REASON_MALFORMED_STORE,
                    f"malformed JSONL at line {line_no}",
                ) from exc
            if not isinstance(payload, dict):
                raise EvidenceError(
                    REASON_MALFORMED_STORE,
                    f"non-object JSONL record at line {line_no}",
                )
            records.append(payload)
        return records

    def append_idempotent(self, bundle: dict[str, Any]) -> dict[str, Any]:
        """Append bundle; same id+digest is no-op; same id different digest HOLD."""
        evidence_id = bundle.get("evidence_id")
        digest = bundle.get("bundle_digest")
        if not isinstance(evidence_id, str) or not isinstance(digest, str):
            raise EvidenceError(
                REASON_MALFORMED_STORE,
                "bundle requires evidence_id and bundle_digest",
            )

        fd = self._acquire_lock()
        try:
            existing = self.read_all()
            for record in existing:
                if record.get("evidence_id") == evidence_id:
                    if record.get("bundle_digest") == digest:
                        return {
                            "written": False,
                            "idempotent": True,
                            "evidence_id": evidence_id,
                            "bundle_digest": digest,
                            "path": str(self.path),
                        }
                    raise EvidenceError(
                        REASON_ID_COLLISION,
                        "same evidence_id with different bundle_digest",
                    )

            line = canonicalize(bundle) + "\n"
            new_body = ""
            if self.path.exists():
                new_body = self.path.read_text(encoding="utf-8")
                if new_body and not new_body.endswith("\n"):
                    raise EvidenceError(
                        REASON_TRUNCATED_LINE,
                        "refusing to append to truncated JSONL store",
                    )
            new_body = new_body + line
            self._atomic_write(new_body)
            return {
                "written": True,
                "idempotent": False,
                "evidence_id": evidence_id,
                "bundle_digest": digest,
                "path": str(self.path),
            }
        finally:
            self._release_lock(fd)

    def _atomic_write(self, body: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        directory = self.path.parent
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=directory,
            delete=False,
            prefix=f".{self.path.name}.",
            suffix=".tmp",
        ) as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
            temp_name = handle.name
        os.replace(temp_name, self.path)

    def find_by_run_id(self, run_id: str) -> list[dict[str, Any]]:
        return [r for r in self.read_all() if r.get("run_id") == run_id]
