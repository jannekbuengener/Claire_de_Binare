"""Run stores for dispatcher lifecycle records (no productive DB)."""

from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Protocol

from tools.agent_control.errors import DispatchError


class RunStore(Protocol):
    def get(self, run_id: str) -> dict[str, Any] | None: ...

    def list_runs(self) -> list[dict[str, Any]]: ...

    def create(self, record: dict[str, Any]) -> dict[str, Any]: ...

    def update_cas(
        self, run_id: str, expected_revision: int, record: dict[str, Any]
    ) -> dict[str, Any]: ...

    def find_by_idempotency(self, key: str) -> dict[str, Any] | None: ...


class InMemoryRunStore:
    """Unit-test store."""

    def __init__(self) -> None:
        self._runs: dict[str, dict[str, Any]] = {}
        self._idempotency: dict[str, str] = {}

    def get(self, run_id: str) -> dict[str, Any] | None:
        record = self._runs.get(run_id)
        return deepcopy(record) if record is not None else None

    def list_runs(self) -> list[dict[str, Any]]:
        return [deepcopy(self._runs[key]) for key in sorted(self._runs)]

    def create(self, record: dict[str, Any]) -> dict[str, Any]:
        run_id = record["run_id"]
        if run_id in self._runs:
            raise DispatchError(
                "DISPATCH_RUN_EXISTS",
                f"run_id already exists: {run_id}",
            )
        key = record.get("idempotency_key")
        if key:
            existing = self._idempotency.get(key)
            if existing:
                raise DispatchError(
                    "DISPATCH_IDEMPOTENCY_CONFLICT",
                    f"idempotency_key already bound to {existing}",
                )
            self._idempotency[key] = run_id
        stored = deepcopy(record)
        self._runs[run_id] = stored
        return deepcopy(stored)

    def update_cas(
        self, run_id: str, expected_revision: int, record: dict[str, Any]
    ) -> dict[str, Any]:
        current = self._runs.get(run_id)
        if current is None:
            raise DispatchError("DISPATCH_RUN_NOT_FOUND", f"unknown run_id: {run_id}")
        if int(current.get("revision", -1)) != int(expected_revision):
            raise DispatchError(
                "DISPATCH_REVISION_MISMATCH",
                f"run {run_id}: expected revision {expected_revision}, "
                f"have {current.get('revision')}",
            )
        if record.get("run_id") != run_id:
            raise DispatchError(
                "DISPATCH_RUN_ID_MISMATCH",
                "record.run_id must match update target",
            )
        if int(record.get("revision", -1)) != expected_revision + 1:
            raise DispatchError(
                "DISPATCH_REVISION_INVALID",
                "updated record.revision must be expected_revision + 1",
            )
        stored = deepcopy(record)
        self._runs[run_id] = stored
        return deepcopy(stored)

    def find_by_idempotency(self, key: str) -> dict[str, Any] | None:
        run_id = self._idempotency.get(key)
        if not run_id:
            return None
        return self.get(run_id)


class JsonFileRunStore:
    """Atomic local JSON state store for CLI smoke tests."""

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists() or self.path.stat().st_size == 0:
            self._write_payload(
                {"schema_id": "cdb.agent_dispatch_store.v1", "runs": {}}
            )

    def _read_payload(self) -> dict[str, Any]:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return {"schema_id": "cdb.agent_dispatch_store.v1", "runs": {}}
        with self.path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict) or "runs" not in payload:
            raise DispatchError(
                "DISPATCH_STORE_INVALID",
                f"invalid run store file: {self.path}",
            )
        return payload

    def _write_payload(self, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        fd, tmp_name = tempfile.mkstemp(
            prefix=self.path.name + ".",
            dir=str(self.path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, self.path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    def get(self, run_id: str) -> dict[str, Any] | None:
        runs = self._read_payload()["runs"]
        record = runs.get(run_id)
        return deepcopy(record) if isinstance(record, dict) else None

    def list_runs(self) -> list[dict[str, Any]]:
        runs = self._read_payload()["runs"]
        return [deepcopy(runs[key]) for key in sorted(runs)]

    def create(self, record: dict[str, Any]) -> dict[str, Any]:
        payload = self._read_payload()
        runs = payload["runs"]
        run_id = record["run_id"]
        if run_id in runs:
            raise DispatchError(
                "DISPATCH_RUN_EXISTS",
                f"run_id already exists: {run_id}",
            )
        key = record.get("idempotency_key")
        if key:
            for existing in runs.values():
                if existing.get("idempotency_key") == key:
                    raise DispatchError(
                        "DISPATCH_IDEMPOTENCY_CONFLICT",
                        f"idempotency_key already bound to {existing['run_id']}",
                    )
        runs[run_id] = deepcopy(record)
        self._write_payload(payload)
        return deepcopy(record)

    def update_cas(
        self, run_id: str, expected_revision: int, record: dict[str, Any]
    ) -> dict[str, Any]:
        payload = self._read_payload()
        runs = payload["runs"]
        current = runs.get(run_id)
        if current is None:
            raise DispatchError("DISPATCH_RUN_NOT_FOUND", f"unknown run_id: {run_id}")
        if int(current.get("revision", -1)) != int(expected_revision):
            raise DispatchError(
                "DISPATCH_REVISION_MISMATCH",
                f"run {run_id}: expected revision {expected_revision}, "
                f"have {current.get('revision')}",
            )
        if int(record.get("revision", -1)) != expected_revision + 1:
            raise DispatchError(
                "DISPATCH_REVISION_INVALID",
                "updated record.revision must be expected_revision + 1",
            )
        runs[run_id] = deepcopy(record)
        self._write_payload(payload)
        return deepcopy(record)

    def find_by_idempotency(self, key: str) -> dict[str, Any] | None:
        for record in self._read_payload()["runs"].values():
            if record.get("idempotency_key") == key:
                return deepcopy(record)
        return None
