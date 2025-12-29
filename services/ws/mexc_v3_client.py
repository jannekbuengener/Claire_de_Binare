"""
MEXC WebSocket V3 Protobuf Client - Production Module

Long-running client for MEXC Spot V3 WebSocket API with:
- Protobuf decoding for public.aggre.deals stream
- Automatic reconnection with exponential backoff
- Ping/pong heartbeat
- Event callback interface
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Callable, Optional

import websockets

# Add generated proto dir to sys.path for pb2 imports
PROTO_GEN_DIR = Path(__file__).resolve().parent / "mexc_proto_gen"
sys.path.insert(0, str(PROTO_GEN_DIR))

import PushDataV3ApiWrapper_pb2 as wrapper_pb2  # type: ignore
import PublicAggreDealsV3Api_pb2 as deals_pb2  # type: ignore

logger = logging.getLogger(__name__)

WS_URL = "wss://wbs-api.mexc.com/ws"


def _pick_list_field(obj, candidates):
    """Helper: pick first available field from candidates"""
    for name in candidates:
        if hasattr(obj, name):
            return getattr(obj, name)
    return None


def decode_message(raw: bytes) -> dict:
    """
    Decode MEXC Protobuf message.

    Strategy:
    1) Try wrapper (PushDataV3ApiWrapper) first
    2) If wrapper doesn't contain deals, try decoding raw as PublicAggreDealsV3Api directly
    """
    w = wrapper_pb2.PushDataV3ApiWrapper()
    try:
        w.ParseFromString(raw)
    except Exception:
        w = None

    if w is not None:
        channel = getattr(w, "channel", "")
        symbol = getattr(w, "symbol", "")

        # Some schemas use oneof; tolerant approach
        publicdeals = getattr(w, "publicdeals", None)
        if publicdeals is None:
            publicdeals = getattr(w, "publicDeals", None)

        if publicdeals:
            deals_list = _pick_list_field(publicdeals, ["dealsList", "deals_list"])
            eventtype = getattr(publicdeals, "eventtype", "") or getattr(publicdeals, "eventType", "")
            return {
                "kind": "wrapper_publicdeals",
                "channel": channel,
                "symbol": symbol,
                "eventtype": eventtype,
                "deals": deals_list if deals_list is not None else [],
            }

    # Fallback: raw message is deals proto directly
    d = deals_pb2.PublicAggreDealsV3Api()
    d.ParseFromString(raw)
    deals_list = _pick_list_field(d, ["dealsList", "deals_list"])
    eventtype = getattr(d, "eventtype", "") or getattr(d, "eventType", "")
    return {"kind": "deals_direct", "eventtype": eventtype, "deals": deals_list if deals_list is not None else []}


def normalize_deal(symbol: str, deal) -> dict:
    """
    Normalize MEXC deal to TradeAgg format.

    MEXC fields: price, quantity, tradetype (1=buy, 2=sell), time (ms)
    CDB format: source, symbol, ts_ms, price, qty, side, raw_ref
    """
    price = str(getattr(deal, "price", ""))
    qty = str(getattr(deal, "quantity", "")) or str(getattr(deal, "qty", ""))
    t = int(getattr(deal, "tradetype", 0) or getattr(deal, "tradeType", 0) or 0)
    ts = int(getattr(deal, "time", 0) or getattr(deal, "ts", 0) or 0)

    side = "unknown"
    if t == 1:
        side = "buy"
    elif t == 2:
        side = "sell"

    return {
        "source": "mexc",
        "symbol": symbol,
        "ts_ms": ts,
        "price": price,
        "qty": qty,
        "side": side,
    }


class MexcV3Client:
    """
    Long-running MEXC WebSocket V3 client with reconnect logic.

    Usage:
        client = MexcV3Client(
            symbol="BTCUSDT",
            interval="100ms",
            on_trade=lambda event: print(event)
        )
        await client.run()
    """

    def __init__(
        self,
        symbol: str = "BTCUSDT",
        interval: str = "100ms",
        on_trade: Optional[Callable[[dict], None]] = None,
        ping_interval: int = 20,
        reconnect_max: int = 10,
    ):
        self.symbol = symbol.upper()
        self.interval = interval
        self.on_trade = on_trade
        self.ping_interval = ping_interval
        self.reconnect_max = reconnect_max

        self.ws = None
        self.connected = False
        self.running = False

        # Metrics
        self.decoded_total = 0
        self.decode_errors_total = 0
        self.last_message_ts = 0

    def get_metrics(self) -> dict:
        """Return current metrics"""
        return {
            "decoded_messages_total": self.decoded_total,
            "decode_errors_total": self.decode_errors_total,
            "ws_connected": 1 if self.connected else 0,
            "last_message_ts_ms": self.last_message_ts,
        }

    async def _ping_loop(self):
        """Heartbeat: send PING every ping_interval seconds"""
        ping = {"method": "PING"}
        while self.running and self.ws:
            try:
                await asyncio.sleep(self.ping_interval)
                if self.ws and not self.ws.closed:
                    await self.ws.send(json.dumps(ping))
                    logger.debug("[ping] sent")
            except Exception as e:
                logger.warning(f"[ping] failed: {e}")
                break

    async def _connect_and_subscribe(self):
        """Connect to WS and subscribe to channel"""
        sub = {
            "method": "SUBSCRIPTION",
            "params": [f"spot@public.aggre.deals.v3.api.pb@{self.interval}@{self.symbol}"],
        }

        logger.info(f"[ws] connecting to {WS_URL}")
        self.ws = await websockets.connect(WS_URL)
        self.connected = True
        logger.info(f"[ws] connected")

        await self.ws.send(json.dumps(sub))
        logger.info(f"[ws] subscribe -> {sub['params'][0]}")

    async def _message_loop(self):
        """Main loop: receive and decode messages"""
        try:
            async for msg in self.ws:
                if isinstance(msg, str):
                    # JSON control messages (ACK, PONG, errors)
                    try:
                        data = json.loads(msg)
                    except Exception:
                        data = {"raw": msg}

                    if data.get("msg") == "PONG":
                        logger.debug("[ws] PONG received")
                        continue

                    if "code" in data or "msg" in data:
                        logger.info(f"[ws] ctrl -> {data}")
                    continue

                # Binary protobuf push
                try:
                    decoded_obj = decode_message(msg)
                    self.decoded_total += 1
                    self.last_message_ts = int(time.time() * 1000)

                    deals = decoded_obj.get("deals") or []
                    if deals and self.on_trade:
                        for deal in deals:
                            event = normalize_deal(self.symbol, deal)
                            self.on_trade(event)

                except Exception as e:
                    self.decode_errors_total += 1
                    logger.error(f"[decode_error] {e}")

        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"[ws] connection closed: {e}")
            self.connected = False
        except Exception as e:
            logger.error(f"[ws] message loop error: {e}")
            self.connected = False

    async def run(self):
        """
        Main run loop with exponential backoff reconnect.

        Runs indefinitely until stopped.
        """
        self.running = True
        backoff = 1  # Start with 1 second

        while self.running:
            try:
                await self._connect_and_subscribe()

                # Start ping task
                ping_task = asyncio.create_task(self._ping_loop())

                # Message loop (blocks until disconnect)
                await self._message_loop()

                # Cleanup
                ping_task.cancel()
                try:
                    await ping_task
                except asyncio.CancelledError:
                    pass

            except Exception as e:
                logger.error(f"[ws] connection error: {e}")
                self.connected = False

            # Exponential backoff reconnect
            if self.running:
                logger.info(f"[ws] reconnecting in {backoff}s...")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self.reconnect_max)  # Cap at reconnect_max

        logger.info("[ws] client stopped")

    def stop(self):
        """Stop the client gracefully"""
        self.running = False
        self.connected = False
