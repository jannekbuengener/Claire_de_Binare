from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
SCANNER_PATH = REPO_ROOT / ".github" / "scripts" / "post_merge_followup_scanner.py"

_SPEC = importlib.util.spec_from_file_location("post_merge_followup_scanner", SCANNER_PATH)
assert _SPEC is not None and _SPEC.loader is not None
scanner = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = scanner
_SPEC.loader.exec_module(scanner)


def _make_pr(number: int, title: str, *paths: str) -> dict[str, object]:
    return {
        "number": number,
        "url": f"https://github.com/jannekbuengener/Claire_de_Binare/pull/{number}",
        "title": title,
        "files": [{"path": path} for path in paths],
    }


def _rule_ids(findings: list[object]) -> set[str]:
    return {finding.rule_id for finding in findings}


def test_digest_only_compose_pin_does_not_trigger_architecture_followup() -> None:
    pr = _make_pr(
        1719,
        "fix(security): pin postgres:15.17-alpine to rebuild digest",
        "infrastructure/compose/compose.blue.yml",
        "infrastructure/compose/base.yml",
        ".github/workflows/security-scan.yml",
    )
    diff_text = """\
diff --git a/infrastructure/compose/compose.blue.yml b/infrastructure/compose/compose.blue.yml
+++ b/infrastructure/compose/compose.blue.yml
@@ -17,7 +17,7 @@ services:
-    image: postgres:15.17-alpine
+    image: postgres:15.17-alpine@sha256:1c52f5ad23db5d7648a63634444af76de48e63b860fccbe3e3a5458b2812eaed
"""

    findings = scanner.detect_findings(pr, diff_text)

    assert "architecture_service_catalog_drift" not in _rule_ids(findings)


def test_digest_only_dockerfile_pin_does_not_trigger_architecture_followup() -> None:
    pr = _make_pr(
        1722,
        "fix(security): pin python:3.11-slim-trixie to rebuild digest",
        "services/allocation/Dockerfile",
        "services/execution/Dockerfile",
    )
    diff_text = """\
diff --git a/services/allocation/Dockerfile b/services/allocation/Dockerfile
+++ b/services/allocation/Dockerfile
@@ -1,4 +1,4 @@
-FROM python:3.11-slim-trixie@sha256:c8271b1f627d0068857dce5b53e14a9558603b527e46f1f901722f935b786a39
+FROM python:3.11-slim-trixie@sha256:233de06753d30d120b1a3ce359d8d3be8bda78524cd8f520c99883bfe33964cf
diff --git a/services/execution/Dockerfile b/services/execution/Dockerfile
+++ b/services/execution/Dockerfile
@@ -1,6 +1,6 @@
-FROM python:3.11-slim-trixie@sha256:c8271b1f627d0068857dce5b53e14a9558603b527e46f1f901722f935b786a39 AS build
+FROM python:3.11-slim-trixie@sha256:233de06753d30d120b1a3ce359d8d3be8bda78524cd8f520c99883bfe33964cf AS build
@@ -21,7 +21,7 @@
-FROM python:3.11-slim-trixie@sha256:c8271b1f627d0068857dce5b53e14a9558603b527e46f1f901722f935b786a39
+FROM python:3.11-slim-trixie@sha256:233de06753d30d120b1a3ce359d8d3be8bda78524cd8f520c99883bfe33964cf
"""

    findings = scanner.detect_findings(pr, diff_text)

    assert "architecture_service_catalog_drift" not in _rule_ids(findings)


def test_tag_change_still_triggers_architecture_followup() -> None:
    pr = _make_pr(
        2001,
        "fix(security): move postgres to new tag",
        "infrastructure/compose/compose.blue.yml",
    )
    diff_text = """\
diff --git a/infrastructure/compose/compose.blue.yml b/infrastructure/compose/compose.blue.yml
+++ b/infrastructure/compose/compose.blue.yml
@@ -17,7 +17,7 @@ services:
-    image: postgres:15.17-alpine@sha256:1c52f5ad23db5d7648a63634444af76de48e63b860fccbe3e3a5458b2812eaed
+    image: postgres:15.18-alpine@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
"""

    findings = scanner.detect_findings(pr, diff_text)

    assert "architecture_service_catalog_drift" in _rule_ids(findings)


def test_new_service_surface_still_triggers_architecture_followup() -> None:
    pr = _make_pr(
        2002,
        "feat(runtime): add operator sidecar",
        "infrastructure/compose/compose.blue.yml",
    )
    diff_text = """\
diff --git a/infrastructure/compose/compose.blue.yml b/infrastructure/compose/compose.blue.yml
+++ b/infrastructure/compose/compose.blue.yml
@@ -30,0 +31,4 @@ services:
+  cdb_sidecar:
+    image: busybox:1.36.1@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
+    container_name: cdb_sidecar
+    restart: unless-stopped
"""

    findings = scanner.detect_findings(pr, diff_text)

    assert "architecture_service_catalog_drift" in _rule_ids(findings)
