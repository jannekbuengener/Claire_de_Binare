from __future__ import annotations

from typing import Protocol


class _RedisPublisher(Protocol):
    def publish(self, channel: str, message: str) -> None: pass

    def xadd(self, stream: str, values: dict[str, str], maxlen: int) -> None: pass


class EnvelopePublisher:
    """Simple wrapper that publishes canonical envelopes to Redis."""

    def __init__(
        self,
        *,
        redis_client: _RedisPublisher,
        mode: str = "stream",
        stream: str = "cdb:envelopes:v1",
        channel: str = "cdb.envelopes.v1",
        maxlen: int = 10000,
    ) -> None:
        self._redis = redis_client
        self._mode = mode.lower()
        self._stream = stream
        self._channel = channel
        self._maxlen = maxlen

    def publish(self, payload: str) -> None:
        if self._mode == "pubsub":
            self._redis.publish(self._channel, payload)
        else:
            self._redis.xadd(self._stream, {"envelope": payload}, maxlen=self._maxlen)
