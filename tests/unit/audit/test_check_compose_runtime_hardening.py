from __future__ import annotations

from pathlib import Path

import pytest

from scripts.audit.check_compose_runtime_hardening import main


def _write(p: Path, text: str) -> Path:
    p.write_text(text, encoding="utf-8")
    return p


def test_guard_passes_for_hardened_app_services_and_profiled_cadvisor(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    blue = _write(
        tmp_path / "compose.blue.yml",
        """
name: cdb-blue
services:
  cdb_market: {security_opt: ["no-new-privileges:true"], cap_drop: ["ALL"], read_only: true, tmpfs: ["/tmp"]}
  cdb_candles: {security_opt: ["no-new-privileges:true"], cap_drop: ["ALL"], read_only: true, tmpfs: ["/tmp"]}
  cdb_regime: {security_opt: ["no-new-privileges:true"], cap_drop: ["ALL"], read_only: true, tmpfs: ["/tmp"]}
  cdb_allocation: {security_opt: ["no-new-privileges:true"], cap_drop: ["ALL"], read_only: true, tmpfs: ["/tmp"]}
  cdb_risk: {security_opt: ["no-new-privileges:true"], cap_drop: ["ALL"], read_only: true, tmpfs: ["/tmp"]}
  cdb_execution: {security_opt: ["no-new-privileges:true"], cap_drop: ["ALL"], read_only: true, tmpfs: ["/tmp"]}
  cdb_db_writer: {security_opt: ["no-new-privileges:true"], cap_drop: ["ALL"], read_only: true, tmpfs: ["/tmp"]}
  cdb_paper_runner: {security_opt: ["no-new-privileges:true"], cap_drop: ["ALL"], read_only: true, tmpfs: ["/tmp"]}
""".lstrip(),
    )
    red = _write(
        tmp_path / "compose.red.yml",
        """
name: cdb-red
services:
  cdb_ws: {security_opt: ["no-new-privileges:true"], cap_drop: ["ALL"], read_only: true, tmpfs: ["/tmp"]}
  cdb_signal: {security_opt: ["no-new-privileges:true"], cap_drop: ["ALL"], read_only: true, tmpfs: ["/tmp"]}
  cdb_reports: {security_opt: ["no-new-privileges:true"], cap_drop: ["ALL"], read_only: true, tmpfs: ["/tmp"]}
  cdb_cadvisor:
    profiles: ["trusted-host-observability"]
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
""".lstrip(),
    )

    rc = main(["--blue", str(blue), "--red", str(red)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "OK:" in out


def test_guard_fails_on_docker_sock_mount_in_default_runtime(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    blue = _write(
        tmp_path / "compose.blue.yml",
        """
name: cdb-blue
services:
  cdb_market:
    security_opt: ["no-new-privileges:true"]
    cap_drop: ["ALL"]
    read_only: true
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
  cdb_candles: {security_opt: ["no-new-privileges:true"], cap_drop: ["ALL"], read_only: true}
  cdb_regime: {security_opt: ["no-new-privileges:true"], cap_drop: ["ALL"], read_only: true}
  cdb_allocation: {security_opt: ["no-new-privileges:true"], cap_drop: ["ALL"], read_only: true}
  cdb_risk: {security_opt: ["no-new-privileges:true"], cap_drop: ["ALL"], read_only: true}
  cdb_execution: {security_opt: ["no-new-privileges:true"], cap_drop: ["ALL"], read_only: true}
  cdb_db_writer: {security_opt: ["no-new-privileges:true"], cap_drop: ["ALL"], read_only: true}
  cdb_paper_runner: {security_opt: ["no-new-privileges:true"], cap_drop: ["ALL"], read_only: true}
""".lstrip(),
    )
    red = _write(
        tmp_path / "compose.red.yml",
        """
name: cdb-red
services:
  cdb_ws: {security_opt: ["no-new-privileges:true"], cap_drop: ["ALL"], read_only: true}
  cdb_signal: {security_opt: ["no-new-privileges:true"], cap_drop: ["ALL"], read_only: true}
  cdb_reports: {security_opt: ["no-new-privileges:true"], cap_drop: ["ALL"], read_only: true}
""".lstrip(),
    )

    rc = main(["--blue", str(blue), "--red", str(red)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "docker.sock" in out

