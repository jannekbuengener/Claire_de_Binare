import os
from pathlib import Path
import pytest

from cdb_utils.secret_loader import read_secret, SecretNotFoundError

def test_env_var_precedence(monkeypatch):
    monkeypatch.setenv("CDB_TEST_SECRET", "env-value")
    assert read_secret("CDB_TEST_SECRET", env_var="CDB_TEST_SECRET") == "env-value"

def test_file_path(tmp_path):
    f = tmp_path / "secret.txt"
    f.write_text("file-value\n")
    assert read_secret("mysecret", file_path=str(f)) == "file-value"

def test_dir_single_file(tmp_path):
    d = tmp_path / "secrets"
    d.mkdir()
    (d / "only").write_text("dir-value\n")
    assert read_secret("only", dir_path=str(d)) == "dir-value"

def test_dir_multiple_files_prefers_named(tmp_path):
    d = tmp_path / "secrets"
    d.mkdir()
    (d / "OTHER").write_text("x")
    (d / "MYNAME").write_text("named")
    assert read_secret("MYNAME", dir_path=str(d)) == "named"

def test_dir_multiple_files_ambiguous(tmp_path):
    d = tmp_path / "secrets"
    d.mkdir()
    (d / "A").write_text("a")
    (d / "B").write_text("b")
    with pytest.raises(SecretNotFoundError):
        read_secret("SOMETHING", dir_path=str(d))

def test_default_returned_if_set():
    assert read_secret("nope", default="fallback") == "fallback"

def test_raises_if_missing():
    with pytest.raises(SecretNotFoundError):
        read_secret("nope")
