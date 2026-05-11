from __future__ import annotations

import json
from pathlib import Path

from scripts.audit import security_alert_issue_candidates as mod


def _base_delta() -> dict:
    return {
        "schema_version": "security_alert_delta.v1",
        "counts": {
            "new_alerts": 2,
            "reopened_alerts": 1,
            "new_groups": 1,
            "escalation_alerts": 1,
        },
        "sources": {
            "current_reference_now_utc": "2026-05-10T12:00:00Z",
        },
        "comparison_skipped_sources": [
            {"source": "dependabot", "reason": "permission denied"}
        ],
        "new_groups": [],
        "escalations": [],
    }


def test_fingerprint_stability() -> None:
    first = mod.build_fingerprint(
        source="code_scanning",
        severity_band="high",
        subject="cve-2026-0001",
        affected_component="library/cdb_signal",
        branch="main",
    )
    second = mod.build_fingerprint(
        source=" code_scanning ",
        severity_band="HIGH",
        subject="CVE-2026-0001",
        affected_component="library/cdb_signal",
        branch="main ",
    )
    assert first == second
    assert len(first) == 16


def test_canonicalization_empty_and_inconsistent_values() -> None:
    assert mod.canonicalize("   ") == "unknown"
    assert mod.canonicalize("  MiXeD   VALUE  ") == "mixed value"
    assert mod.canonicalize(None) == "unknown"


def test_secret_and_sensitive_fields_are_not_present() -> None:
    delta = _base_delta()
    delta["escalation_needed"] = True
    delta["escalations"] = [
        {
            "source": "secret_scanning",
            "severity": "critical",
            "subject": "ghp_secret_token",
            "affected_component": "repo",
            "branch": "main",
            "raw": {"token": "never"},
            "locations_url": "https://example.invalid/location",
        }
    ]
    payload = mod.build_output_payload(delta=delta, candidates=mod.build_candidates(delta))
    serialized = json.dumps(payload)
    assert payload["candidate_count"] == 0
    assert "locations_url" not in serialized
    assert "token" not in serialized


def test_dedupe_marker_shape() -> None:
    delta = _base_delta()
    delta["new_groups"] = [
        {
            "source": "dependabot",
            "subject": "openssl",
            "branch": "main",
        }
    ]
    candidate = mod.build_candidates(delta)[0]
    marker = candidate["dedupe_marker"]
    assert marker.startswith("<!-- cdb-security-alert-group:")
    assert marker.endswith(" -->")
    assert candidate["fingerprint"] in marker


def test_body_safe_schema() -> None:
    delta = _base_delta()
    delta["new_groups"] = [
        {
            "source": "dependabot",
            "subject": "urllib3",
            "branch": "main",
        }
    ]
    candidate = mod.build_candidates(delta)[0]
    body = candidate["body_safe_fields"]
    required = {
        "generated_from_readout",
        "current_reference_now_utc",
        "source",
        "severity",
        "severity_band",
        "counts",
        "subject",
        "affected_component",
        "branch",
        "fingerprint",
        "next_action",
        "references",
    }
    assert required <= set(body.keys())
    assert "locations_url" not in body
    assert "raw" not in body


def test_no_candidate_from_comparison_skipped_sources_only() -> None:
    delta = _base_delta()
    candidates = mod.build_candidates(delta)
    assert candidates == []


def test_no_candidate_from_secret_scanning_payload() -> None:
    delta = _base_delta()
    delta["new_groups"] = [
        {
            "source": "secret_scanning",
            "subject": "token leak",
            "branch": "main",
        }
    ]
    delta["escalation_needed"] = True
    delta["escalations"] = [
        {
            "source": "secret_scanning",
            "severity": "critical",
            "subject": "token leak",
            "affected_component": "repo",
            "branch": "main",
        }
    ]
    assert mod.build_candidates(delta) == []


def test_reopened_high_critical_creates_candidate() -> None:
    delta = _base_delta()
    delta["escalation_needed"] = True
    delta["reopened_alerts"] = [
        {
            "source": "code_scanning",
            "number": 77,
            "affected_component": "library/cdb_market",
        }
    ]
    delta["escalations"] = [
        {
            "source": "code_scanning",
            "number": 77,
            "severity": "critical",
            "subject": "cve-2026-1111",
            "branch": "main",
        }
    ]
    candidates = mod.build_candidates(delta)
    assert len(candidates) == 1
    assert candidates[0]["severity"] == "critical"
    assert candidates[0]["affected_component"] == "library/cdb_market"
    assert "Refs #2289" in candidates[0]["references"]


def test_new_groups_creates_candidate() -> None:
    delta = _base_delta()
    delta["new_groups"] = [
        {
            "source": "dependabot",
            "subject": "jinja2",
            "branch": "main",
        }
    ]
    candidates = mod.build_candidates(delta)
    assert len(candidates) == 1
    assert candidates[0]["source"] == "dependabot"
    assert candidates[0]["subject"] == "jinja2"


def test_new_group_and_escalation_share_resolved_component_no_duplicates() -> None:
    delta = _base_delta()
    delta["escalation_needed"] = True
    delta["new_groups"] = [
        {
            "source": "code_scanning",
            "subject": "cve-2026-9999",
            "branch": "main",
        }
    ]
    delta["new_alerts"] = [
        {
            "source": "code_scanning",
            "number": 88,
            "affected_component": "library/cdb_signal",
        }
    ]
    delta["escalations"] = [
        {
            "source": "code_scanning",
            "number": 88,
            "severity": "high",
            "subject": "cve-2026-9999",
            "branch": "main",
        }
    ]

    candidates = mod.build_candidates(delta)
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate["affected_component"] == "library/cdb_signal"
    assert candidate["fingerprint"] == mod.build_fingerprint(
        source="code_scanning",
        severity_band="high",
        subject="cve-2026-9999",
        affected_component="library/cdb_signal",
        branch="main",
    )


def test_new_group_and_escalation_references_and_labels_remain_consistent() -> None:
    delta = _base_delta()
    delta["escalation_needed"] = True
    delta["new_groups"] = [
        {
            "source": "code_scanning",
            "subject": "cve-2026-4545",
            "branch": "main",
        },
        {
            "source": "code_scanning",
            "subject": "cve-2026-3030",
            "branch": "main",
        },
    ]
    delta["new_alerts"] = [
        {
            "source": "code_scanning",
            "number": 12,
            "affected_component": "library/cdb_signal",
        },
        {
            "source": "code_scanning",
            "number": 11,
            "affected_component": "library/grafana-curl-layer",
        },
    ]
    delta["escalations"] = [
        {
            "source": "code_scanning",
            "number": 12,
            "severity": "high",
            "subject": "cve-2026-4545",
            "branch": "main",
        },
        {
            "source": "code_scanning",
            "number": 11,
            "severity": "high",
            "subject": "cve-2026-3030",
            "branch": "main",
        },
    ]
    candidates = mod.build_candidates(delta)
    assert len(candidates) == 2

    by_subject = {c["subject"]: c for c in candidates}
    py_candidate = by_subject["cve-2026-4545"]
    grafana_candidate = by_subject["cve-2026-3030"]

    assert "Refs #2290" in py_candidate["references"]
    assert "status:blocked" in py_candidate["suggested_labels"]
    assert all(not ref.lower().startswith("closes ") for ref in py_candidate["references"])

    assert "Refs #2292" in grafana_candidate["references"]
    assert all(
        not ref.lower().startswith("closes ") for ref in grafana_candidate["references"]
    )


def test_trivy_grafana_candidate_may_reference_2292_without_closing() -> None:
    delta = _base_delta()
    delta["escalation_needed"] = True
    delta["new_alerts"] = [
        {
            "source": "code_scanning",
            "number": 11,
            "affected_component": "library/grafana-curl-layer",
        }
    ]
    delta["escalations"] = [
        {
            "source": "code_scanning",
            "number": 11,
            "severity": "high",
            "subject": "cve-2026-3030",
            "branch": "main",
        }
    ]
    candidate = mod.build_candidates(delta)[0]
    assert "Refs #2292" in candidate["references"]
    assert all(not ref.lower().startswith("closes ") for ref in candidate["references"])


def test_python_base_image_trivy_candidate_may_reference_2290_without_closing() -> None:
    delta = _base_delta()
    delta["escalation_needed"] = True
    delta["new_alerts"] = [
        {
            "source": "code_scanning",
            "number": 12,
            "affected_component": "library/cdb_signal",
        }
    ]
    delta["escalations"] = [
        {
            "source": "code_scanning",
            "number": 12,
            "severity": "high",
            "subject": "cve-2026-4545",
            "branch": "main",
        }
    ]
    candidate = mod.build_candidates(delta)[0]
    assert "Refs #2290" in candidate["references"]
    assert "status:blocked" in candidate["suggested_labels"]
    assert all(not ref.lower().startswith("closes ") for ref in candidate["references"])


def test_title_body_are_bounded_and_do_not_embed_raw_objects() -> None:
    delta = _base_delta()
    delta["escalation_needed"] = True
    very_long_subject = "cve-2026-1212-" + ("x" * 300)
    delta["escalations"] = [
        {
            "source": "code_scanning",
            "severity": "critical",
            "subject": very_long_subject,
            "affected_component": "library/cdb_execution",
            "branch": "main",
            "raw": {"nested": "value"},
        }
    ]
    candidate = mod.build_candidates(delta)[0]
    assert len(candidate["suggested_title"]) <= 220
    assert isinstance(candidate["body_safe_fields"], dict)
    assert "raw" not in candidate["body_safe_fields"]


def test_escalation_component_uses_package_name_or_image_when_safe() -> None:
    delta = _base_delta()
    delta["escalation_needed"] = True
    delta["escalations"] = [
        {
            "source": "code_scanning",
            "number": 1,
            "severity": "high",
            "subject": "urllib3-vuln",
            "package_name": "urllib3",
            "branch": "main",
        },
        {
            "source": "dependabot",
            "number": 2,
            "severity": "high",
            "subject": "base-image-vuln",
            "image": "ghcr.io/acme/base:3.12",
            "branch": "main",
        },
    ]
    candidates = mod.build_candidates(delta)
    components = {c["subject"]: c["affected_component"] for c in candidates}
    assert components["urllib3-vuln"] == "urllib3"
    assert components["base-image-vuln"] == "ghcr.io/acme/base:3.12"


def test_escalation_component_stays_unknown_without_safe_source() -> None:
    delta = _base_delta()
    delta["escalation_needed"] = True
    delta["escalations"] = [
        {
            "source": "dependabot",
            "number": 9,
            "severity": "high",
            "subject": "jinja2",
            "branch": "main",
        }
    ]
    candidate = mod.build_candidates(delta)[0]
    assert candidate["affected_component"] == "unknown"


def test_component_mapping_rejects_location_and_raw_fields() -> None:
    delta = _base_delta()
    delta["escalation_needed"] = True
    delta["new_alerts"] = [
        {
            "source": "code_scanning",
            "number": 500,
            "affected_component": "library/cdb_execution",
        }
    ]
    delta["escalations"] = [
        {
            "source": "code_scanning",
            "number": 500,
            "severity": "high",
            "subject": "cve-2026-5050",
            "locations_url": "https://example.invalid/location/500",
            "raw": {"affected_component": "sensitive"},
            "branch": "main",
        }
    ]
    candidate = mod.build_candidates(delta)[0]
    assert candidate["affected_component"] == "library/cdb_execution"
    assert "https://example.invalid/location/500" not in json.dumps(candidate)


def test_cli_writes_output(tmp_path: Path) -> None:
    delta_path = tmp_path / mod.INPUT_FILENAME
    out_dir = tmp_path / "out"
    delta = _base_delta()
    delta["new_groups"] = [
        {"source": "dependabot", "subject": "urllib3", "branch": "main"}
    ]
    delta_path.write_text(json.dumps(delta), encoding="utf-8")
    payload = mod.generate_candidates(input_path=delta_path, out_dir=out_dir)
    out_path = out_dir / mod.OUTPUT_FILENAME
    assert out_path.exists()
    assert payload["candidate_count"] == 1

