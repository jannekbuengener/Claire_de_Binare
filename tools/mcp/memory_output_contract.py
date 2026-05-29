"""Agent output contract for memory/evidence MCP tools.

Issue: #2701
Parent: #2606 (Langzeitgedaechtnis / Persistent Agent Memory)
Cross-refs: #2605 (Context MCP), agents/AGENTS.md § Brain Evidence Gate

Enforces a consistent response envelope on memory/evidence MCP tools so
agents must surface ``memory_id`` (per-record), guarded ``source``,
``trust``/``trust_level``, and ``limitations`` when operating in
Memory/Evidence scope.

Guardrails:
    - Read-only contract validation; no DB writes, no mutations.
    - Caller-spoofed ``brain_source`` / ``metadata.source`` cannot upgrade
      the source label to ``surrealdb-local`` (enforced by
      ``derive_guarded_source_label`` — this contract validates the output).
    - LR remains NO-GO.
"""

from __future__ import annotations

from typing import Any, Mapping

MEMORY_OUTPUT_CONTRACT_VERSION = "memory-output-contract/v1"

REQUIRED_ENVELOPE_FIELDS = frozenset({"tool", "status", "metadata"})
REQUIRED_METADATA_FIELDS = frozenset({"source", "read_only"})

ALLOWED_SOURCE_LABELS = frozenset(
    {
        "in_memory",
        "surrealdb-local",
        "surrealdb-local-unavailable",
    }
)

_DEFAULT_LIMITATIONS = [
    "Memory is provided as context, not as authoritative truth.",
    "stale/superseded memory is flagged but not auto-removed.",
    "LR remains NO-GO; no live-go or Echtgeld-GO implied.",
]


class MemoryOutputContractError(ValueError):
    """Raised when a memory/evidence MCP response violates the output contract."""


def default_limitations() -> list[str]:
    """Return the canonical limitations list for memory/evidence tools."""
    return list(_DEFAULT_LIMITATIONS)


def validate_memory_output_contract(response: Mapping[str, Any]) -> list[str]:
    """Validate that *response* satisfies the memory agent output contract.

    Returns a list of violation descriptions. An empty list means the
    response is contract-compliant.
    """
    violations: list[str] = []

    for field in REQUIRED_ENVELOPE_FIELDS:
        if field not in response:
            violations.append(f"missing required envelope field: {field}")

    if response.get("status") in ("error", "refused"):
        return violations

    metadata = response.get("metadata")
    if not isinstance(metadata, Mapping):
        violations.append("metadata must be a mapping")
        return violations

    for field in REQUIRED_METADATA_FIELDS:
        if field not in metadata:
            violations.append(f"missing required metadata field: {field}")

    source = metadata.get("source")
    if source is not None and source not in ALLOWED_SOURCE_LABELS:
        violations.append(
            f"metadata.source '{source}' is not in allowed set: "
            f"{sorted(ALLOWED_SOURCE_LABELS)}"
        )

    result = response.get("result")
    if not isinstance(result, Mapping):
        violations.append("result must be a mapping for ok responses")
        return violations

    if "limitations" not in result:
        violations.append("missing required field: result.limitations")

    # Trust check: required only when the result carries memory/trust context.
    # Evidence-resolve and claim-resolve do not produce memory-trust fields —
    # the contract requires only source + limitations for those tools.
    # Note: claim-resolve has a ``confidence_summary`` with numeric stats
    # (min/max/avg/count) which is NOT memory-trust context.
    _has_trust_scope = (
        "matched_memory" in result
        or "trust_level" in result
        or "memory_summary" in result
    )
    if _has_trust_scope:
        trust_level = result.get("trust_level")
        trust_in_summary = (result.get("memory_summary") or {}).get(
            "overall_trust"
        )
        if trust_level is None and trust_in_summary is None:
            violations.append(
                "missing trust information: need trust_level or "
                "memory_summary.overall_trust"
            )

    matched_memory = result.get("matched_memory")
    if isinstance(matched_memory, list):
        for idx, record in enumerate(matched_memory):
            if not isinstance(record, Mapping):
                continue
            if "memory_id" not in record:
                violations.append(
                    f"matched_memory[{idx}] missing required field: memory_id"
                )
            if "trust_level" not in record:
                violations.append(
                    f"matched_memory[{idx}] missing required field: trust_level"
                )

    return violations


def enforce_memory_output_contract(response: Mapping[str, Any]) -> None:
    """Raise ``MemoryOutputContractError`` if *response* violates the contract."""
    violations = validate_memory_output_contract(response)
    if violations:
        raise MemoryOutputContractError(
            f"Memory output contract violations: {'; '.join(violations)}"
        )


def stamp_limitations(
    result: dict[str, Any],
    *,
    extra: list[str] | None = None,
) -> dict[str, Any]:
    """Add ``limitations`` to *result* if not already present.

    Merges default limitations with any *extra* entries.  Existing
    ``limitations`` in *result* are preserved and extended.
    """
    existing = list(result.get("limitations") or [])
    defaults = default_limitations()
    merged = list(dict.fromkeys(existing + defaults + (extra or [])))
    result["limitations"] = merged
    return result
