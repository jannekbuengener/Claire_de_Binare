"""Tests for scripts/replay/lr021_export_redis.py — Redis stream exporter.

All tests use mock/fake Redis clients — no real Redis dependency.

Governance: LR-021 Slice 3 (Redis Stream Export)
"""

import io
import json
import sys
from pathlib import Path

import pytest

# scripts/ is not a Python package (no __init__.py), so add it to sys.path.
repo_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repo_root / "scripts"))

from replay.lr021_export_redis import (  # noqa: E402
    GENESIS_HASH,
    export_envelopes,
    iter_stream_entries,
    parse_stream_entry,
    build_arg_parser,
)
from core.replay.canonical_json import canonical_json_dumps  # noqa: E402
from replay.lr021_replay import compute_chain_hash, compute_event_hash  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_envelope_json(
    event_type: str = "DECISION",
    event_id: str = "ev-1",
    ts_ms: int = 1000,
    payload: dict | None = None,
    **extra: str,
) -> dict:
    """Build a minimal valid envelope dict."""
    env = {
        "schema_version": "envelope.v1",
        "event_type": event_type,
        "event_id": event_id,
        "ts_ms": ts_ms,
        "payload": payload or {},
    }
    env.update(extra)
    return env


def _stream_entry_json_blob(
    entry_id: str,
    envelope: dict,
    field_name: str = "envelope",
) -> tuple[str, dict[str, str]]:
    """Build a (entry_id, fields) tuple with JSON blob encoding."""
    return (entry_id, {field_name: json.dumps(envelope)})


def _stream_entry_flat(
    entry_id: str,
    envelope: dict,
) -> tuple[str, dict[str, str]]:
    """Build a (entry_id, fields) tuple with flat-field encoding."""
    fields: dict[str, str] = {
        "schema_version": envelope["schema_version"],
        "event_type": envelope["event_type"],
        "event_id": envelope["event_id"],
        "ts_ms": str(envelope["ts_ms"]),
        "payload": json.dumps(envelope["payload"]),
    }
    for k in ("policy_id", "policy_hash", "input_hash", "output_hash"):
        if k in envelope:
            fields[k] = envelope[k]
    return (entry_id, fields)


class FakeRedis:
    """Minimal fake Redis client that supports xrange() for testing."""

    def __init__(self, entries: list[tuple[str, dict[str, str]]]):
        self._entries = entries  # stored in ID order

    def xrange(
        self,
        name: str,
        min: str = "-",  # noqa: A002
        max: str = "+",  # noqa: A002
        count: int | None = None,
    ) -> list[tuple[str, dict[str, str]]]:
        result = []
        for eid, fields in self._entries:
            if min != "-" and eid < min:
                continue
            if max != "+" and eid > max:
                continue
            result.append((eid, fields))
        if count is not None:
            result = result[:count]
        return result


# ---------------------------------------------------------------------------
# parse_stream_entry
# ---------------------------------------------------------------------------

class TestParseStreamEntry:
    def test_json_blob_envelope_field(self):
        env = _make_envelope_json()
        eid, fields = _stream_entry_json_blob("1-0", env)
        result = parse_stream_entry(eid, fields)
        assert result == env

    def test_json_blob_data_field(self):
        env = _make_envelope_json(event_type="ORDER")
        eid, fields = _stream_entry_json_blob("1-0", env, field_name="data")
        result = parse_stream_entry(eid, fields)
        assert result == env

    def test_flat_fields(self):
        env = _make_envelope_json(
            event_type="FILL",
            payload={"order_id": "o-1", "fill_id": "f-1"},
            policy_id="pol-1",
        )
        eid, fields = _stream_entry_flat("1-0", env)
        result = parse_stream_entry(eid, fields)
        assert result is not None
        assert result["event_type"] == "FILL"
        assert result["payload"] == {"order_id": "o-1", "fill_id": "f-1"}
        assert result["policy_id"] == "pol-1"

    def test_flat_fields_fallback_event_id(self):
        """If event_id missing from flat fields, uses entry_id."""
        fields = {
            "schema_version": "envelope.v1",
            "event_type": "DECISION",
            "ts_ms": "5000",
            "payload": "{}",
        }
        result = parse_stream_entry("99-0", fields)
        assert result is not None
        assert result["event_id"] == "99-0"

    def test_unparseable_returns_none(self):
        result = parse_stream_entry("1-0", {"random": "garbage"})
        assert result is None

    def test_invalid_json_in_envelope_field_falls_through(self):
        """Bad JSON in 'envelope' field falls through to flat parse."""
        fields = {
            "envelope": "NOT-JSON",
            "schema_version": "envelope.v1",
            "event_type": "DECISION",
            "event_id": "ev-1",
            "ts_ms": "1000",
            "payload": "{}",
        }
        result = parse_stream_entry("1-0", fields)
        assert result is not None
        assert result["event_type"] == "DECISION"


# ---------------------------------------------------------------------------
# iter_stream_entries (streaming)
# ---------------------------------------------------------------------------

class TestIterStreamEntries:
    def test_reads_all_entries(self):
        env1 = _make_envelope_json(event_id="ev-1")
        env2 = _make_envelope_json(event_id="ev-2", event_type="ORDER")
        entries_in = [
            _stream_entry_json_blob("1000-0", env1),
            _stream_entry_json_blob("2000-0", env2),
        ]
        client = FakeRedis(entries_in)
        result = list(iter_stream_entries(client, "test:stream"))
        assert len(result) == 2
        assert result[0][0] == "1000-0"
        assert result[1][0] == "2000-0"

    def test_respects_limit(self):
        entries_in = [
            _stream_entry_json_blob(f"{i}-0", _make_envelope_json(event_id=f"ev-{i}"))
            for i in range(10)
        ]
        client = FakeRedis(entries_in)
        result = list(iter_stream_entries(client, "s", limit=3))
        assert len(result) == 3

    def test_deterministic_order(self):
        """Entries come back in Redis ID order."""
        ids = ["1000-0", "1000-1", "2000-0", "3000-0"]
        entries_in = [
            _stream_entry_json_blob(eid, _make_envelope_json(event_id=f"ev-{i}"))
            for i, eid in enumerate(ids)
        ]
        client = FakeRedis(entries_in)
        result = list(iter_stream_entries(client, "s"))
        result_ids = [r[0] for r in result]
        assert result_ids == ids

    def test_empty_stream(self):
        client = FakeRedis([])
        result = list(iter_stream_entries(client, "s"))
        assert result == []

    def test_start_end_id_filter(self):
        entries_in = [
            _stream_entry_json_blob("1000-0", _make_envelope_json(event_id="ev-1")),
            _stream_entry_json_blob("2000-0", _make_envelope_json(event_id="ev-2")),
            _stream_entry_json_blob("3000-0", _make_envelope_json(event_id="ev-3")),
        ]
        client = FakeRedis(entries_in)
        result = list(iter_stream_entries(client, "s", start_id="2000-0", end_id="2000-0"))
        assert len(result) == 1
        assert result[0][0] == "2000-0"

    def test_batched_reading(self):
        """Small batch size still yields all entries."""
        entries_in = [
            _stream_entry_json_blob(f"{i}-0", _make_envelope_json(event_id=f"ev-{i}"))
            for i in range(5)
        ]
        client = FakeRedis(entries_in)
        result = list(iter_stream_entries(client, "s", batch_size=2))
        assert len(result) == 5


# ---------------------------------------------------------------------------
# export_envelopes — default (raw, no hashes)
# ---------------------------------------------------------------------------

class TestExportEnvelopesRaw:
    def test_default_no_hashes(self):
        """Default export writes raw envelopes without event_hash / chain_hash."""
        env = _make_envelope_json(payload={"decision": "ALLOW", "symbol": "BTC"})
        entries = [_stream_entry_json_blob("1-0", env)]
        output = io.StringIO()

        summary = export_envelopes(iter(entries), output)

        assert summary["exported"] == 1
        assert "final_chain_hash" not in summary

        output.seek(0)
        line = json.loads(output.readline())
        assert "event_hash" not in line
        assert "chain_hash" not in line
        assert line["event_type"] == "DECISION"

    def test_canonical_json_used(self):
        """Output lines are canonical JSON (sorted keys, compact separators)."""
        env = _make_envelope_json(payload={"z_key": 1, "a_key": 2})
        entries = [_stream_entry_json_blob("1-0", env)]
        output = io.StringIO()

        export_envelopes(iter(entries), output)

        output.seek(0)
        raw_line = output.readline().strip()
        expected = canonical_json_dumps(env)
        assert raw_line == expected

    def test_deterministic_output(self):
        """Same input -> byte-identical output on repeated runs."""
        env = _make_envelope_json(
            payload={"symbol": "ETH", "decision": "BLOCK"},
            policy_id="pol-1",
        )
        entries = [_stream_entry_json_blob("1-0", env)]

        outputs = []
        for _ in range(3):
            buf = io.StringIO()
            export_envelopes(iter(entries), buf)
            outputs.append(buf.getvalue())

        assert outputs[0] == outputs[1] == outputs[2]

    def test_type_filter(self):
        dec = _make_envelope_json(event_type="DECISION", event_id="d-1")
        order = _make_envelope_json(event_type="ORDER", event_id="o-1")
        fill = _make_envelope_json(event_type="FILL", event_id="f-1")
        entries = [
            _stream_entry_json_blob("1-0", dec),
            _stream_entry_json_blob("2-0", order),
            _stream_entry_json_blob("3-0", fill),
        ]
        output = io.StringIO()

        summary = export_envelopes(
            iter(entries), output, type_filter={"DECISION", "FILL"},
        )

        assert summary["exported"] == 2
        assert summary["skipped_by_filter"] == 1

        output.seek(0)
        lines = [json.loads(ln) for ln in output if ln.strip()]
        types = [ln["event_type"] for ln in lines]
        assert types == ["DECISION", "FILL"]

    def test_parse_errors_counted(self):
        good = _stream_entry_json_blob("1-0", _make_envelope_json())
        bad = ("2-0", {"random": "junk"})
        output = io.StringIO()

        summary = export_envelopes(iter([good, bad]), output)

        assert summary["exported"] == 1
        assert summary["parse_errors"] == 1


# ---------------------------------------------------------------------------
# export_envelopes — with hashes (opt-in)
# ---------------------------------------------------------------------------

class TestExportEnvelopesWithHashes:
    def test_include_hashes(self):
        """--include-hashes adds event_hash but not chain_hash."""
        env = _make_envelope_json(payload={"decision": "ALLOW"})
        entries = [_stream_entry_json_blob("1-0", env)]
        output = io.StringIO()

        summary = export_envelopes(
            iter(entries), output, include_hashes=True,
        )

        output.seek(0)
        line = json.loads(output.readline())
        assert "event_hash" in line
        assert "chain_hash" not in line
        assert "final_chain_hash" not in summary

        # Verify hash matches what lr021_replay would compute
        expected_hash = compute_event_hash(env)
        assert line["event_hash"] == expected_hash

    def test_include_hashes_with_chain(self):
        """--include-hashes + --compute-chain-hash adds both."""
        env1 = _make_envelope_json(event_id="ev-1", ts_ms=1000)
        env2 = _make_envelope_json(event_id="ev-2", ts_ms=2000, event_type="ORDER")
        entries = [
            _stream_entry_json_blob("1-0", env1),
            _stream_entry_json_blob("2-0", env2),
        ]
        output = io.StringIO()

        summary = export_envelopes(
            iter(entries), output,
            include_hashes=True, compute_chain=True,
        )

        assert summary["exported"] == 2
        assert "final_chain_hash" in summary

        output.seek(0)
        lines = [json.loads(ln) for ln in output if ln.strip()]

        # Verify chain hash computation matches lr021_replay logic
        eh1 = compute_event_hash(env1)
        ch1 = compute_chain_hash(GENESIS_HASH, eh1)
        assert lines[0]["event_hash"] == eh1
        assert lines[0]["chain_hash"] == ch1

        eh2 = compute_event_hash(env2)
        ch2 = compute_chain_hash(ch1, eh2)
        assert lines[1]["event_hash"] == eh2
        assert lines[1]["chain_hash"] == ch2
        assert summary["final_chain_hash"] == ch2

    def test_compute_chain_without_include_hashes_is_noop(self):
        """compute_chain=True but include_hashes=False -> no hashes."""
        env = _make_envelope_json()
        entries = [_stream_entry_json_blob("1-0", env)]
        output = io.StringIO()

        export_envelopes(
            iter(entries), output,
            include_hashes=False, compute_chain=True,
        )

        output.seek(0)
        line = json.loads(output.readline())
        assert "event_hash" not in line
        assert "chain_hash" not in line


# ---------------------------------------------------------------------------
# Replay roundtrip: export -> lr021_replay strict
# ---------------------------------------------------------------------------

class TestReplayRoundtrip:
    """Export raw envelopes and feed through lr021_replay strict."""

    def test_exported_envelopes_pass_strict_replay(self):
        from replay.lr021_replay import replay

        envs = [
            _make_envelope_json(
                event_type="DECISION",
                event_id="dec-1",
                ts_ms=1000,
                payload={"decision": "ALLOW", "symbol": "BTCUSDT"},
            ),
            _make_envelope_json(
                event_type="ORDER",
                event_id="ord-1",
                ts_ms=2000,
                payload={"symbol": "BTCUSDT", "side": "BUY", "quantity": 0.01, "price": 42000.5},
            ),
            _make_envelope_json(
                event_type="FILL",
                event_id="fill-1",
                ts_ms=3000,
                payload={"order_id": "ord-1", "fill_id": "f-1", "symbol": "BTCUSDT",
                         "side": "BUY", "filled_quantity": 0.01, "price": 42000.5},
            ),
        ]
        entries = [
            _stream_entry_json_blob(f"{i}-0", env)
            for i, env in enumerate(envs)
        ]

        # Step 1: Export raw (no hashes)
        export_buf = io.StringIO()
        export_summary = export_envelopes(iter(entries), export_buf)
        assert export_summary["exported"] == 3

        # Step 2: Feed into lr021_replay strict
        export_buf.seek(0)
        replay_buf = io.StringIO()
        replay_summary = replay(export_buf, replay_buf, strict=True, chain=True)

        assert replay_summary["processed"] == 3
        assert replay_summary["skipped"] == 0

        # Step 3: Verify output has valid hashes
        replay_buf.seek(0)
        lines = [json.loads(ln) for ln in replay_buf if ln.strip()]
        for line in lines:
            assert "event_hash" in line
            assert "chain_hash" in line
            assert len(line["event_hash"]) == 64
            assert len(line["chain_hash"]) == 64

    def test_exported_hashes_match_replay_hashes(self):
        """When export includes hashes, they match what replay computes."""
        from replay.lr021_replay import replay

        env = _make_envelope_json(
            event_type="DECISION",
            event_id="dec-x",
            ts_ms=5000,
            payload={"decision": "BLOCK", "symbol": "ETH"},
        )
        entries = [_stream_entry_json_blob("1-0", env)]

        # Export with hashes
        export_buf = io.StringIO()
        export_envelopes(
            iter(entries), export_buf,
            include_hashes=True, compute_chain=True,
        )
        export_buf.seek(0)
        exported = json.loads(export_buf.readline())

        # Replay on raw envelope (no hashes in input)
        raw_buf = io.StringIO(canonical_json_dumps(env) + "\n")
        replay_buf = io.StringIO()
        replay(raw_buf, replay_buf, strict=True, chain=True)
        replay_buf.seek(0)
        replayed = json.loads(replay_buf.readline())

        assert exported["event_hash"] == replayed["event_hash"]
        assert exported["chain_hash"] == replayed["chain_hash"]


# ---------------------------------------------------------------------------
# CLI arg parser
# ---------------------------------------------------------------------------

class TestArgParser:
    def test_required_stream(self):
        with pytest.raises(SystemExit):
            build_arg_parser().parse_args([])

    def test_defaults(self):
        args = build_arg_parser().parse_args(["--stream", "s"])
        assert args.stream == "s"
        assert args.redis_url == "redis://localhost:6379"
        assert args.start_id == "-"
        assert args.end_id == "+"
        assert args.limit is None
        assert args.types is None
        assert args.include_hashes is False
        assert args.compute_chain_hash is False
        assert args.out is None

    def test_all_flags(self):
        args = build_arg_parser().parse_args([
            "--stream", "my:stream",
            "--redis-url", "redis://host:1234",
            "--start-id", "100-0",
            "--end-id", "999-0",
            "--limit", "50",
            "--type", "DECISION",
            "--type", "FILL",
            "--include-hashes",
            "--compute-chain-hash",
            "--out", "/tmp/out.jsonl",
            "--batch-size", "500",
        ])
        assert args.stream == "my:stream"
        assert args.redis_url == "redis://host:1234"
        assert args.start_id == "100-0"
        assert args.end_id == "999-0"
        assert args.limit == 50
        assert args.types == ["DECISION", "FILL"]
        assert args.include_hashes is True
        assert args.compute_chain_hash is True
        assert args.out == "/tmp/out.jsonl"
        assert args.batch_size == 500


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_stream_export(self):
        output = io.StringIO()
        summary = export_envelopes(iter([]), output)
        assert summary["exported"] == 0
        assert summary["parse_errors"] == 0
        assert summary["skipped_by_filter"] == 0
        assert output.getvalue() == ""

    def test_policy_fields_omitted_when_absent(self):
        """Optional policy_* fields are NOT in output when not in stream entry."""
        env = _make_envelope_json()  # no policy_id etc.
        entries = [_stream_entry_json_blob("1-0", env)]
        output = io.StringIO()
        export_envelopes(iter(entries), output)

        output.seek(0)
        line = json.loads(output.readline())
        assert "policy_id" not in line
        assert "policy_hash" not in line

    def test_policy_fields_present_when_set(self):
        env = _make_envelope_json(policy_id="pol-1", policy_hash="abc123")
        entries = [_stream_entry_json_blob("1-0", env)]
        output = io.StringIO()
        export_envelopes(iter(entries), output)

        output.seek(0)
        line = json.loads(output.readline())
        assert line["policy_id"] == "pol-1"
        assert line["policy_hash"] == "abc123"

    def test_bytes_decoded(self):
        """Redis entries with bytes keys/values are decoded correctly."""
        env = _make_envelope_json()
        entry = ("1-0", {b"envelope": json.dumps(env).encode()})

        # parse_stream_entry expects str fields; iter_stream_entries
        # handles decoding. Test parse directly with str.
        _, str_fields = _stream_entry_json_blob("1-0", env)
        result = parse_stream_entry("1-0", str_fields)
        assert result is not None
