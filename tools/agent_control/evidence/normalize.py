"""Usage/cost and provenance normalization for evidence bundles."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
from typing import Any

from tools.agent_control.errors import EvidenceError
from tools.agent_control.evidence.codes import (
    COST_STATUS,
    REASON_USAGE_INVALID,
)


def _provenance(
    *,
    trust_class: str,
    source: str,
    reference: str | None = None,
    digest: str | None = None,
) -> dict[str, Any]:
    return {
        "trust_class": trust_class,
        "source": source,
        "reference": reference,
        "digest": digest,
    }


def normalize_usage_cost(
    raw: dict[str, Any] | None,
    *,
    scenario: str | None = None,
) -> dict[str, Any]:
    """Normalize usage/cost deterministically without inventing numbers."""
    raw = dict(raw or {})
    iterations = int(raw.get("iterations") or 0)
    tool_calls = int(raw.get("tool_calls") or 0)
    if iterations < 0 or tool_calls < 0:
        raise EvidenceError(REASON_USAGE_INVALID, "negative usage counters")

    tokens: dict[str, Any] = {}
    for key in ("input_tokens", "output_tokens", "cache_tokens", "total_tokens"):
        if key not in raw or raw[key] is None:
            tokens[key] = {
                "value": None,
                "status": "UNAVAILABLE",
                "provenance": _provenance(
                    trust_class="derived",
                    source="evidence.normalize_usage_cost",
                ),
            }
            continue
        value = int(raw[key])
        if value < 0:
            raise EvidenceError(REASON_USAGE_INVALID, f"negative token field {key}")
        tokens[key] = {
            "value": value,
            "status": "CONFIRMED",
            "provenance": _provenance(
                trust_class="provider_reported",
                source="provider.usage",
            ),
        }

    if (
        tokens["total_tokens"]["value"] is not None
        and tokens["input_tokens"]["value"] is not None
        and tokens["output_tokens"]["value"] is not None
        and tokens["total_tokens"]["value"]
        < tokens["input_tokens"]["value"] + tokens["output_tokens"]["value"]
    ):
        raise EvidenceError(
            REASON_USAGE_INVALID,
            "total_tokens inconsistent with input/output tokens",
        )

    cost_raw = raw.get("cost")
    currency = raw.get("currency")
    if scenario == "mock" and cost_raw is None:
        cost = {
            "amount": None,
            "currency": None,
            "status": "NOT_APPLICABLE",
            "provenance": _provenance(
                trust_class="derived",
                source="evidence.mock_cost",
            ),
        }
    elif cost_raw is None:
        cost = {
            "amount": None,
            "currency": None,
            "status": "UNAVAILABLE",
            "provenance": _provenance(
                trust_class="derived",
                source="evidence.normalize_usage_cost",
            ),
        }
    else:
        cost = _normalize_cost_amount(cost_raw, currency)

    return {
        "iterations": iterations,
        "tool_calls": tool_calls,
        "tokens": tokens,
        "cost": cost,
    }


def _normalize_cost_amount(cost_raw: Any, currency: Any) -> dict[str, Any]:
    if isinstance(cost_raw, float):
        raise EvidenceError(REASON_USAGE_INVALID, "float cost rejected")
    if isinstance(cost_raw, bool):
        raise EvidenceError(REASON_USAGE_INVALID, "boolean cost rejected")
    try:
        if isinstance(cost_raw, Decimal):
            amount = format(cost_raw, "f")
        elif isinstance(cost_raw, int):
            amount = str(cost_raw)
        elif isinstance(cost_raw, str):
            # Reject float-looking scientific; accept decimal strings.
            Decimal(cost_raw)
            if "e" in cost_raw.lower() or "." in cost_raw and "E" in cost_raw:
                raise EvidenceError(REASON_USAGE_INVALID, "scientific cost rejected")
            amount = cost_raw
        else:
            raise EvidenceError(REASON_USAGE_INVALID, "unsupported cost type")
    except (InvalidOperation, EvidenceError) as exc:
        if isinstance(exc, EvidenceError):
            raise
        raise EvidenceError(REASON_USAGE_INVALID, "invalid cost amount") from exc

    if currency is None or currency == "":
        raise EvidenceError(REASON_USAGE_INVALID, "cost requires currency")
    if not isinstance(currency, str):
        raise EvidenceError(REASON_USAGE_INVALID, "currency must be string")
    return {
        "amount": amount,
        "currency": currency,
        "status": "CONFIRMED",
        "provenance": _provenance(
            trust_class="provider_reported",
            source="provider.usage.cost",
        ),
    }


def normalize_changed_files(files: Any) -> list[str]:
    if files is None:
        return []
    if not isinstance(files, list):
        raise EvidenceError(REASON_USAGE_INVALID, "changed_files must be a list")
    cleaned = sorted({str(item) for item in files if item is not None and str(item)})
    return cleaned


def claim(
    *,
    value: Any,
    trust_class: str,
    source: str,
    reference: str | None = None,
    digest: str | None = None,
) -> dict[str, Any]:
    return {
        "value": deepcopy(value),
        "provenance": _provenance(
            trust_class=trust_class,
            source=source,
            reference=reference,
            digest=digest,
        ),
    }


def ensure_cost_status(status: str) -> str:
    if status not in COST_STATUS:
        raise EvidenceError(REASON_USAGE_INVALID, f"unknown cost status {status!r}")
    return status
