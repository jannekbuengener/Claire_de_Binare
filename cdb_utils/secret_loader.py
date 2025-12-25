"""
cdb_utils.secret_loader
Unified secret loader with file / dir / env fallback.

Behavior:
- Prefer explicit env var if provided and set
- Then prefer single file at given file_path
- Then prefer single file inside dir_path:
  - If dir contains exactly one file -> use it
  - If dir contains multiple -> prefer file named like `name`, otherwise error
- Optional default can be returned instead of raising

Exceptions: SecretNotFoundError on missing secret
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

class SecretNotFoundError(RuntimeError):
    """Raised when a secret cannot be found by any strategy."""

def read_secret(
    name: str,
    *,
    env_var: Optional[str] = None,
    file_path: Optional[Path | str] = None,
    dir_path: Optional[Path | str] = None,
    default: Optional[str] = None,
) -> str:
    """
    Lade ein Secret mit der folgenden Priorität:
      1. Environment variable (wenn env_var angegeben und gesetzt)
      2. Exakter File-Pfad (file_path)
      3. Directory (dir_path) — wenn ein File enthalten ist, oder ein File mit dem Namen `name`
      4. default (wenn angegeben)
    Wirf SecretNotFoundError, falls nichts gefunden wird und kein default gesetzt ist.

    Parameters:
      name: logischer Name des Secrets (z.B. 'REDIS_PASSWORD')
      env_var: optionaler Env-Variablenname
      file_path: Pfad zu einer Datei mit dem Secret-Inhalt
      dir_path: Pfad zu einem Verzeichnis mit Secret-Files
      default: optionaler Default-Wert (wird zurückgegeben statt Exception)

    Returns:
      Secret-Inhalt als String (ohne trailing newline bereinigt)
    """
    # 1) env
    if env_var:
        val = os.getenv(env_var)
        if val is not None:
            return val.rstrip("\n")

    # 2) file path
    if file_path:
        p = Path(file_path)
        if p.is_file():
            return p.read_text(encoding="utf-8").rstrip("\n")

    # 3) dir path
    if dir_path:
        d = Path(dir_path)
        if d.is_dir():
            # prefer file with same name
            candidate = d / name
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8").rstrip("\n")
            # list regular files
            files = [f for f in sorted(d.iterdir()) if f.is_file()]
            if len(files) == 1:
                return files[0].read_text(encoding="utf-8").rstrip("\n")
            if len(files) > 1:
                raise SecretNotFoundError(
                    f"Multiple files in secret dir {d!s}; none match '{name}'. "
                    "Please choose a single-file dir or a file named after the secret."
                )

    # 4) default or fail
    if default is not None:
        return default

    raise SecretNotFoundError(
        f"Secret '{name}' not found (env={env_var}, file={file_path}, dir={dir_path})"
    )
