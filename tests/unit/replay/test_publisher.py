"""Tests that EnvelopePublisher forwards payloads to Redis clients."""

from unittest.mock import MagicMock

from core.replay.publisher import EnvelopePublisher


def test_pubsub_mode_uses_publish():
    client = MagicMock()
    publisher = EnvelopePublisher(
        redis_client=client,
        mode="pubsub",
        stream="stream.envelopes",
        channel="channel.envelopes",
    )

    publisher.publish("payload")

    client.publish.assert_called_once_with("channel.envelopes", "payload")
    assert client.xadd.call_count == 0


def test_stream_mode_uses_xadd_with_envelope_field():
    client = MagicMock()
    publisher = EnvelopePublisher(
        redis_client=client,
        mode="stream",
        stream="stream.envelopes",
        channel="channel.envelopes",
        maxlen=42,
    )

    publisher.publish("payload")

    client.xadd.assert_called_once_with(
        "stream.envelopes", {"envelope": "payload"}, maxlen=42
    )
    assert client.publish.call_count == 0
