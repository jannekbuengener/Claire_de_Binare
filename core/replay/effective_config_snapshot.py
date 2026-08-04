"""Effective Config snapshot + fingerprint for ARVP provenance (#4151).

Captures the *resolved* experiment-relevant configuration after defaults and
overrides (not raw source hashes alone). Deterministic, secret-safe, fail-closed.

Resolution order (later wins):
  code_default → compose → env

Compose values are read from the canonical BLUE/RED compose files so the
repo-default snapshot is stable across hosts. Explicit ``env_overrides`` and
``compose_overrides`` allow experiment/run linkage without reading live secrets.
``env`` (explicit) beats compose so experiment overrides are observable.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Sequence

import yaml

from core.contracts.primary_breakout_v1_config import PrimaryBreakoutV1Config
from core.replay.canonical_json import canonical_hash
from core.replay.dataset_identity import (
    assert_content_payload_secret_safe,
    collect_forbidden_evidence_keys,
)

SCHEMA_VERSION = "cdb.effective_config_snapshot.v1"

REQUIRED_SECTIONS: tuple[str, ...] = (
    "schema_version",
    "compose",
    "environment_redacted",
    "risk",
    "allocation",
    "regime",
    "signal",
    "execution",
    "override_order",
    "snapshot_fingerprint",
)

# Later layers win. Explicit env/experiment overrides beat compose file values.
DEFAULT_OVERRIDE_ORDER: tuple[str, ...] = ("code_default", "compose", "env")

COMPOSE_BLUE_REL = Path("infrastructure/compose/compose.blue.yml")
COMPOSE_RED_REL = Path("infrastructure/compose/compose.red.yml")

# Env keys allowed in environment_redacted (allowlist).
_SAFE_ENV_KEYS: frozenset[str] = frozenset(
    {
        "ENV",
        "LOG_LEVEL",
        "MOCK_TRADING",
        "USE_REAL_BALANCE",
        "USE_LIVE_BALANCE",
        "TRACE_CONTRACT_V1_ENABLED",
        "PAPER_AUTO_UNWIND",
        "MAX_POSITION_PCT",
        "MAX_TOTAL_EXPOSURE_PCT",
        "MAX_EXPOSURE_PCT",
        "MAX_DAILY_DRAWDOWN_PCT",
        "STOP_LOSS_PCT",
        "EARLY_LIVE_MAX_ALLOC",
        "TEST_BALANCE",
        "REGIME_ADX_PERIOD",
        "REGIME_ATR_PERIOD",
        "REGIME_ADX_TREND_THRESHOLD",
        "REGIME_ADX_RANGE_THRESHOLD",
        "REGIME_ATR_HIGH_VOL_THRESHOLD",
        "REGIME_CONFIRMATION_BARS",
        "ALLOCATION_REGIME_MIN_STABLE_SECONDS",
        "ALLOCATION_RULES_JSON",
        "SIGNAL_STRATEGY_ID",
        "SIGNAL_ADAPTER_ID",
        "SIGNAL_ENTRY_LOOKBACK_MIN",
        "SIGNAL_EXIT_LOOKBACK_MIN",
        "SIGNAL_BREAKOUT_BUFFER",
        "SIGNAL_MIN_MINUTES_BETWEEN_ENTRIES",
        "SIGNAL_TRADE_SIDE_MODE",
        "SIGNAL_THRESHOLD_PCT",
        "SIGNAL_MIN_VOLUME",
        "CDB_KILL_SWITCH_STATE_FILE",
    }
)

_SENSITIVE_KEY_RE = re.compile(
    r"(password|secret|token|api[_-]?key|dsn|database_url|connection_string)",
    re.IGNORECASE,
)

_COMPOSE_DEFAULT_RE = re.compile(r"^\$\{[A-Za-z_][A-Za-z0-9_]*:-(.*)\}$")


class EffectiveConfigSnapshotError(ValueError):
    """Raised when an effective-config snapshot is incomplete or unsafe."""


def _deep_merge(base: Mapping[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = dict(base)
    for key, value in overlay.items():
        if key in out and isinstance(out[key], Mapping) and isinstance(value, Mapping):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _coerce_scalar(raw: Any) -> Any:
    if not isinstance(raw, str):
        return raw
    text = raw.strip()
    match = _COMPOSE_DEFAULT_RE.match(text)
    if match:
        text = match.group(1)
    lowered = text.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text


def _parse_allocation_rules(raw: Any) -> Any:
    if isinstance(raw, Mapping):
        return dict(raw)
    if isinstance(raw, str):
        text = raw.strip()
        match = _COMPOSE_DEFAULT_RE.match(text)
        if match:
            text = match.group(1)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise EffectiveConfigSnapshotError(
                f"ALLOCATION_RULES_JSON is not valid JSON: {exc}"
            ) from exc
        if not isinstance(parsed, Mapping) or not parsed:
            raise EffectiveConfigSnapshotError(
                "ALLOCATION_RULES_JSON must be a non-empty object"
            )
        return dict(parsed)
    raise EffectiveConfigSnapshotError("ALLOCATION_RULES_JSON missing or invalid")


def code_default_layers() -> dict[str, Any]:
    """Static code-level defaults (no process env, no secrets)."""
    pb1 = PrimaryBreakoutV1Config()
    return {
        "environment_redacted": {
            "ENV": "development",
            "LOG_LEVEL": "INFO",
            "MOCK_TRADING": "true",
            "USE_REAL_BALANCE": "false",
            "USE_LIVE_BALANCE": "false",
            "TRACE_CONTRACT_V1_ENABLED": "1",
            "PAPER_AUTO_UNWIND": "false",
        },
        "risk": {
            "max_position_pct": 0.10,
            "max_total_exposure_pct": 0.30,
            "max_daily_drawdown_pct": 0.05,
            "stop_loss_pct": 0.02,
            "early_live_max_alloc": 0.02,
            "paper_auto_unwind": False,
            "use_live_balance": False,
            "use_real_balance": False,
            "test_balance": 10000.0,
            "kill_switch_state_file": "/app/kill_switch/.cdb_kill_switch.state",
        },
        "allocation": {
            "regime_min_stable_seconds": 60,
            "rules": {
                "paper": {
                    "STEADY_BULLISH": 0.3,
                    "TREND": 0.3,
                    "VOLATILE_RANGE": 0.1,
                    "RANGE": 0.1,
                    "HIGH_VOL_CHAOTIC": 0.02,
                    "UNKNOWN": 0.0,
                }
            },
        },
        "regime": {
            "adx_period": 14,
            "atr_period": 14,
            "adx_trend_threshold": 25.0,
            "adx_range_threshold": 20.0,
            "atr_high_vol_threshold": 0.001,
            "confirmation_bars": 3,
        },
        "signal": {
            "strategy_id": pb1.strategy_id,
            "symbol": pb1.symbol,
            "entry_lookback_minutes": pb1.entry_lookback_minutes,
            "exit_lookback_minutes": pb1.exit_lookback_minutes,
            "breakout_buffer": pb1.breakout_buffer,
            "min_minutes_between_entries": pb1.min_minutes_between_entries,
            "trade_side_mode": pb1.trade_side_mode,
            "adapter_id": "momentum_builtin",
            "threshold_pct": 0.005,
            "min_volume": 0,
        },
        "execution": {
            "mock_trading": True,
            "use_real_balance": False,
            "trace_contract_v1_enabled": True,
            "kill_switch_state_file": "/app/kill_switch/.cdb_kill_switch.state",
        },
    }


def _load_compose_doc(path: Path) -> Mapping[str, Any]:
    if not path.is_file():
        raise EffectiveConfigSnapshotError(f"compose file missing: {path}")
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise EffectiveConfigSnapshotError(f"compose YAML parse failed: {exc}") from exc
    if not isinstance(doc, Mapping):
        raise EffectiveConfigSnapshotError(f"compose root must be object: {path}")
    return doc


def _raw_service_environment(doc: Mapping[str, Any], service: str) -> dict[str, Any]:
    services = doc.get("services")
    if not isinstance(services, Mapping):
        return {}
    svc = services.get(service)
    if not isinstance(svc, Mapping):
        return {}
    env = svc.get("environment")
    if not isinstance(env, Mapping):
        return {}
    return {str(k): v for k, v in env.items()}


def _safe_env_subset(raw_env: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in raw_env.items():
        if key not in _SAFE_ENV_KEYS:
            continue
        if _SENSITIVE_KEY_RE.search(key):
            continue
        out[key] = _coerce_scalar(value)
    return out


def extract_compose_env_layers(repo_root: Path) -> dict[str, Any]:
    """Pull safe service env from compose.blue + compose.red into section overlays."""
    blue = _load_compose_doc(repo_root / COMPOSE_BLUE_REL)
    red = _load_compose_doc(repo_root / COMPOSE_RED_REL)

    regime_raw = _raw_service_environment(blue, "cdb_regime")
    alloc_raw = _raw_service_environment(blue, "cdb_allocation")
    risk_raw = _raw_service_environment(blue, "cdb_risk")
    exec_raw = _raw_service_environment(blue, "cdb_execution")
    signal_raw = _raw_service_environment(red, "cdb_signal")

    regime_env = _safe_env_subset(regime_raw)
    alloc_env = _safe_env_subset(alloc_raw)
    risk_env = _safe_env_subset(risk_raw)
    exec_env = _safe_env_subset(exec_raw)
    signal_env = _safe_env_subset(signal_raw)

    environment_redacted: dict[str, str] = {}
    for layer in (regime_env, alloc_env, risk_env, exec_env, signal_env):
        for key, value in layer.items():
            if isinstance(value, bool):
                environment_redacted[key] = "true" if value else "false"
            else:
                environment_redacted[key] = str(value)

    allocation_rules = None
    if "ALLOCATION_RULES_JSON" in alloc_raw:
        allocation_rules = _parse_allocation_rules(alloc_raw["ALLOCATION_RULES_JSON"])

    return {
        "environment_redacted": environment_redacted,
        "risk": {
            "paper_auto_unwind": bool(
                _coerce_scalar(risk_raw.get("PAPER_AUTO_UNWIND", False))
            ),
            "kill_switch_state_file": str(
                risk_raw.get(
                    "CDB_KILL_SWITCH_STATE_FILE",
                    "/app/kill_switch/.cdb_kill_switch.state",
                )
            ),
        },
        "allocation": {
            "regime_min_stable_seconds": int(
                _coerce_scalar(
                    alloc_raw.get("ALLOCATION_REGIME_MIN_STABLE_SECONDS", 60)
                )
            ),
            **({"rules": allocation_rules} if allocation_rules is not None else {}),
        },
        "regime": {
            "adx_period": int(_coerce_scalar(regime_raw.get("REGIME_ADX_PERIOD", 14))),
            "atr_period": int(_coerce_scalar(regime_raw.get("REGIME_ATR_PERIOD", 14))),
            "adx_trend_threshold": float(
                _coerce_scalar(regime_raw.get("REGIME_ADX_TREND_THRESHOLD", 25.0))
            ),
            "adx_range_threshold": float(
                _coerce_scalar(regime_raw.get("REGIME_ADX_RANGE_THRESHOLD", 20.0))
            ),
            "atr_high_vol_threshold": float(
                _coerce_scalar(regime_raw.get("REGIME_ATR_HIGH_VOL_THRESHOLD", 0.001))
            ),
            "confirmation_bars": int(
                _coerce_scalar(regime_raw.get("REGIME_CONFIRMATION_BARS", 3))
            ),
        },
        "signal": {
            "strategy_id": str(
                _coerce_scalar(
                    signal_raw.get("SIGNAL_STRATEGY_ID", "primary_breakout_v1")
                )
            ),
            "adapter_id": str(
                _coerce_scalar(signal_raw.get("SIGNAL_ADAPTER_ID", "momentum_builtin"))
            ),
            "entry_lookback_minutes": int(
                _coerce_scalar(signal_raw.get("SIGNAL_ENTRY_LOOKBACK_MIN", 240))
            ),
            "exit_lookback_minutes": int(
                _coerce_scalar(signal_raw.get("SIGNAL_EXIT_LOOKBACK_MIN", 120))
            ),
            "breakout_buffer": float(
                _coerce_scalar(signal_raw.get("SIGNAL_BREAKOUT_BUFFER", 0.0005))
            ),
            "min_minutes_between_entries": int(
                _coerce_scalar(signal_raw.get("SIGNAL_MIN_MINUTES_BETWEEN_ENTRIES", 60))
            ),
            "trade_side_mode": str(
                _coerce_scalar(signal_raw.get("SIGNAL_TRADE_SIDE_MODE", "long_only"))
            ),
            "threshold_pct": float(
                _coerce_scalar(signal_raw.get("SIGNAL_THRESHOLD_PCT", 0.005))
            ),
            "min_volume": float(_coerce_scalar(signal_raw.get("SIGNAL_MIN_VOLUME", 0))),
        },
        "execution": {
            "mock_trading": bool(_coerce_scalar(exec_raw.get("MOCK_TRADING", True))),
            "use_real_balance": bool(
                _coerce_scalar(exec_raw.get("USE_REAL_BALANCE", False))
            ),
            "trace_contract_v1_enabled": bool(
                _coerce_scalar(exec_raw.get("TRACE_CONTRACT_V1_ENABLED", True))
            ),
            "kill_switch_state_file": str(
                exec_raw.get(
                    "CDB_KILL_SWITCH_STATE_FILE",
                    "/app/kill_switch/.cdb_kill_switch.state",
                )
            ),
        },
    }


def _env_override_layers(env_overrides: Mapping[str, Any] | None) -> dict[str, Any]:
    if not env_overrides:
        return {}
    safe: dict[str, str] = {}
    for key, value in env_overrides.items():
        key_str = str(key)
        if key_str not in _SAFE_ENV_KEYS:
            if _SENSITIVE_KEY_RE.search(key_str):
                raise EffectiveConfigSnapshotError(
                    f"refusing sensitive env override key: {key_str}"
                )
            continue
        safe[key_str] = str(value)

    layers: dict[str, Any] = {"environment_redacted": dict(safe)}
    if "MOCK_TRADING" in safe:
        layers["execution"] = {
            "mock_trading": str(safe["MOCK_TRADING"]).lower() == "true"
        }
    if "USE_REAL_BALANCE" in safe:
        layers.setdefault("execution", {})["use_real_balance"] = (
            str(safe["USE_REAL_BALANCE"]).lower() == "true"
        )
    if "PAPER_AUTO_UNWIND" in safe:
        layers["risk"] = {
            "paper_auto_unwind": str(safe["PAPER_AUTO_UNWIND"]).lower() == "true"
        }
    if "MAX_POSITION_PCT" in safe:
        layers.setdefault("risk", {})["max_position_pct"] = float(
            safe["MAX_POSITION_PCT"]
        )
    if "SIGNAL_ENTRY_LOOKBACK_MIN" in safe:
        layers["signal"] = {
            "entry_lookback_minutes": int(safe["SIGNAL_ENTRY_LOOKBACK_MIN"])
        }
    if "SIGNAL_EXIT_LOOKBACK_MIN" in safe:
        layers.setdefault("signal", {})["exit_lookback_minutes"] = int(
            safe["SIGNAL_EXIT_LOOKBACK_MIN"]
        )
    if "SIGNAL_BREAKOUT_BUFFER" in safe:
        layers.setdefault("signal", {})["breakout_buffer"] = float(
            safe["SIGNAL_BREAKOUT_BUFFER"]
        )
    if "SIGNAL_STRATEGY_ID" in safe:
        layers.setdefault("signal", {})["strategy_id"] = safe["SIGNAL_STRATEGY_ID"]
    if "REGIME_ATR_HIGH_VOL_THRESHOLD" in safe:
        layers["regime"] = {
            "atr_high_vol_threshold": float(safe["REGIME_ATR_HIGH_VOL_THRESHOLD"])
        }
    if "ALLOCATION_RULES_JSON" in safe:
        layers["allocation"] = {
            "rules": _parse_allocation_rules(safe["ALLOCATION_RULES_JSON"])
        }
    return layers


def fingerprint_snapshot_body(body: Mapping[str, Any]) -> str:
    """SHA-256 of the snapshot body excluding ``snapshot_fingerprint``."""
    payload = {k: v for k, v in body.items() if k != "snapshot_fingerprint"}
    return canonical_hash(payload)


def validate_effective_config_snapshot(snapshot: Mapping[str, Any]) -> None:
    """Fail-closed structural + secret + fingerprint integrity validation."""
    if not isinstance(snapshot, Mapping):
        raise EffectiveConfigSnapshotError(
            "effective config snapshot must be an object"
        )

    missing = [k for k in REQUIRED_SECTIONS if k not in snapshot]
    if missing:
        raise EffectiveConfigSnapshotError(
            "incomplete effective config snapshot; missing sections: "
            + ", ".join(missing)
        )

    if snapshot.get("schema_version") != SCHEMA_VERSION:
        raise EffectiveConfigSnapshotError(
            f"unsupported schema_version: {snapshot.get('schema_version')!r}"
        )

    superficial_only = set(snapshot.keys()) <= {
        "parameter_hash",
        "env_subset",
        "dataset_fingerprint",
        "schema_version",
        "snapshot_fingerprint",
    }
    if superficial_only:
        raise EffectiveConfigSnapshotError(
            "superficial effective config snapshot rejected "
            "(parameter/env/dataset hash alone is insufficient)"
        )

    for section in ("compose", "risk", "allocation", "regime", "signal", "execution"):
        value = snapshot.get(section)
        if not isinstance(value, Mapping) or not value:
            raise EffectiveConfigSnapshotError(
                f"effective config section '{section}' must be non-empty object"
            )

    override = snapshot.get("override_order")
    if not isinstance(override, Sequence) or isinstance(override, (str, bytes)):
        raise EffectiveConfigSnapshotError(
            "override_order must be a non-string sequence"
        )
    if not override:
        raise EffectiveConfigSnapshotError("override_order must be non-empty")

    env = snapshot.get("environment_redacted")
    if not isinstance(env, Mapping):
        raise EffectiveConfigSnapshotError("environment_redacted must be an object")

    try:
        assert_content_payload_secret_safe(snapshot)
    except ValueError as exc:
        raise EffectiveConfigSnapshotError(str(exc)) from exc

    forbidden = collect_forbidden_evidence_keys(snapshot)
    if forbidden:
        raise EffectiveConfigSnapshotError(
            "snapshot contains forbidden secret/path keys: " + ", ".join(forbidden)
        )
    for key in env:
        if _SENSITIVE_KEY_RE.search(str(key)):
            raise EffectiveConfigSnapshotError(
                f"environment_redacted contains sensitive key: {key}"
            )

    fp = snapshot.get("snapshot_fingerprint")
    if not isinstance(fp, str) or len(fp) != 64:
        raise EffectiveConfigSnapshotError("snapshot_fingerprint must be 64-char hex")
    expected = fingerprint_snapshot_body(snapshot)
    if fp != expected:
        raise EffectiveConfigSnapshotError(
            "snapshot_fingerprint does not match canonical body hash"
        )


def build_effective_config_snapshot(
    repo_root: Path | str,
    *,
    env_overrides: Mapping[str, Any] | None = None,
    compose_overrides: Mapping[str, Any] | None = None,
    override_order: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Build a complete, secret-safe, fingerprintable effective-config snapshot.

    Resolution is deterministic for a given repo tree + explicit overrides.
    Live process environment is intentionally ignored (host drift).
    """
    root = Path(repo_root)
    order = tuple(override_order or DEFAULT_OVERRIDE_ORDER)
    if list(order) != list(DEFAULT_OVERRIDE_ORDER):
        # Keep contract stable; custom orders must still declare the three layers.
        for required in DEFAULT_OVERRIDE_ORDER:
            if required not in order:
                raise EffectiveConfigSnapshotError(
                    f"override_order missing required layer: {required}"
                )

    code = code_default_layers()
    env_layer = _env_override_layers(env_overrides)
    compose_layer = extract_compose_env_layers(root)
    if compose_overrides:
        compose_layer = _deep_merge(compose_layer, dict(compose_overrides))

    layer_map: dict[str, Mapping[str, Any]] = {
        "code_default": code,
        "env": env_layer,
        "compose": compose_layer,
    }

    merged: dict[str, Any] = {}
    for name in order:
        merged = _deep_merge(merged, layer_map.get(name, {}))

    if "allocation" not in merged or not merged["allocation"].get("rules"):
        raise EffectiveConfigSnapshotError(
            "resolved allocation.rules missing after defaults/overrides"
        )

    snapshot: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "compose": {
            "blue": COMPOSE_BLUE_REL.as_posix(),
            "red": COMPOSE_RED_REL.as_posix(),
        },
        "environment_redacted": dict(merged.get("environment_redacted") or {}),
        "risk": dict(merged.get("risk") or {}),
        "allocation": dict(merged.get("allocation") or {}),
        "regime": dict(merged.get("regime") or {}),
        "signal": dict(merged.get("signal") or {}),
        "execution": dict(merged.get("execution") or {}),
        "override_order": list(order),
        "sources": {
            "code_default": True,
            "env_overrides_applied": bool(env_overrides),
            "compose_blue": COMPOSE_BLUE_REL.as_posix(),
            "compose_red": COMPOSE_RED_REL.as_posix(),
        },
    }
    snapshot["snapshot_fingerprint"] = fingerprint_snapshot_body(snapshot)
    validate_effective_config_snapshot(snapshot)
    return snapshot


def link_snapshot_to_evidence(
    snapshot: Mapping[str, Any],
    *,
    experiment_id: str | None = None,
    run_id: str | None = None,
    preflight_report_fingerprint: str | None = None,
) -> dict[str, Any]:
    """Attach non-hashed evidence linkage metadata (does not alter fingerprint)."""
    linked = dict(snapshot)
    evidence: MutableMapping[str, Any] = {}
    if experiment_id:
        evidence["experiment_id"] = experiment_id
    if run_id:
        evidence["run_id"] = run_id
    if preflight_report_fingerprint:
        evidence["preflight_report_fingerprint"] = preflight_report_fingerprint
    if evidence:
        linked["evidence_links"] = dict(evidence)
    return linked
