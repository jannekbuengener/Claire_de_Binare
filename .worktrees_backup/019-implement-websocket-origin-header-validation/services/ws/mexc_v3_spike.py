import asyncio
import json
import time
from pathlib import Path
import sys

import websockets

# make generated pb2 importable
GEN_DIR = Path(__file__).resolve().parent / "mexc_proto_gen"
sys.path.insert(0, str(GEN_DIR))

import PushDataV3ApiWrapper_pb2 as wrapper_pb2  # type: ignore
import PublicAggreDealsV3Api_pb2 as deals_pb2   # type: ignore


WS_URL = "wss://wbs-api.mexc.com/ws"  # MEXC Spot V3 WS base endpoint


def _pick_list_field(obj, candidates):
    for name in candidates:
        if hasattr(obj, name):
            return getattr(obj, name)
    return None


def decode_message(raw: bytes):
    """
    Strategy:
    1) Try wrapper (PushDataV3ApiWrapper) first.
    2) If wrapper doesn't contain deals, try decoding raw as PublicAggreDealsV3Api directly.
    """
    w = wrapper_pb2.PushDataV3ApiWrapper()
    try:
        w.ParseFromString(raw)
    except Exception:
        w = None

    if w is not None:
        # common fields shown in MEXC docs examples: channel, symbol, sendTime
        channel = getattr(w, "channel", "")
        symbol = getattr(w, "symbol", "")

        # Some schemas use a oneof; we do a tolerant approach:
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

    # fallback: raw message is deals proto directly
    d = deals_pb2.PublicAggreDealsV3Api()
    d.ParseFromString(raw)
    deals_list = _pick_list_field(d, ["dealsList", "deals_list"])
    eventtype = getattr(d, "eventtype", "") or getattr(d, "eventType", "")
    return {"kind": "deals_direct", "eventtype": eventtype, "deals": deals_list if deals_list is not None else []}


def normalize_deal(symbol: str, deal):
    # docs: price, quantity, tradetype (1 buy, 2 sell), time (ms)
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


async def run(symbol="BTCUSDT", interval="100ms", duration_s=600):
    # MEXC requires uppercase symbol
    symbol = symbol.upper()

    decoded = 0
    decode_errors = 0
    last_ts = 0
    connected = 0
    last_sample_log = 0

    sub = {
        "method": "SUBSCRIPTION",
        "params": [f"spot@public.aggre.deals.v3.api.pb@{interval}@{symbol}"],
    }
    ping = {"method": "PING"}

    async with websockets.connect(WS_URL) as ws:
        connected = 1
        print(f"[ws] connected url={WS_URL}")

        await ws.send(json.dumps(sub))
        print(f"[ws] subscribe -> {sub['params'][0]}")

        async def ping_loop():
            while True:
                await asyncio.sleep(20)
                await ws.send(json.dumps(ping))

        ping_task = asyncio.create_task(ping_loop())

        start = time.time()
        try:
            while time.time() - start < duration_s:
                msg = await ws.recv()

                if isinstance(msg, str):
                    # ACK / PONG / errors
                    try:
                        data = json.loads(msg)
                    except Exception:
                        data = {"raw": msg}
                    if data.get("msg") == "PONG":
                        continue
                    if "code" in data or "msg" in data:
                        print(f"[ws] ctrl -> {data}")
                    continue

                # binary protobuf push
                try:
                    decoded_obj = decode_message(msg)
                    decoded += 1
                    last_ts = int(time.time() * 1000)

                    deals = decoded_obj.get("deals") or []
                    if deals:
                        # log one sample event every ~30s
                        now = time.time()
                        if now - last_sample_log >= 30:
                            ev = normalize_deal(symbol, deals[0])
                            print(f"[sample] {ev}")
                            last_sample_log = now
                except Exception as e:
                    decode_errors += 1
                    print(f"[decode_error] {e}")

            print("[done] duration reached")
        finally:
            ping_task.cancel()

    connected = 0
    print(f"[metrics] ws_connected={connected} decoded_messages_total={decoded} decode_errors_total={decode_errors} last_message_ts_ms={last_ts}")


if __name__ == "__main__":
    asyncio.run(run())
