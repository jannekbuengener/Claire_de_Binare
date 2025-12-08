import os
import json
import time
import threading
import sys
from collections import defaultdict, deque
from datetime import datetime
import pandas as pd
import requests
import redis
from websocket import WebSocketApp
from flask import Flask, jsonify

REST_BASE = os.getenv("MEXC_BASE", "https://contract.mexc.com")
WS_URL = "wss://contract.mexc.com/edge"
LOOKBACK_MIN = int(os.getenv("LOOKBACK_MIN", "15"))
KL_INTERVAL = "Min1"
DATA_STALL_SEC = 30

klines = defaultdict(lambda: deque(maxlen=LOOKBACK_MIN + 5))
symbols = []
last_tick_ts = 0

# Redis client für Event-Publishing
redis_client = None
try:
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        password=os.getenv("REDIS_PASSWORD") or None,
        db=int(os.getenv("REDIS_DB", "0")),
        decode_responses=True,
        socket_connect_timeout=3,
    )
    redis_client.ping()
    print("✓ Redis verbunden - market_data Events werden publiziert")
except Exception as e:
    print(f"⚠ Redis nicht verfügbar: {e} - Events werden nicht publiziert")
    redis_client = None

# --- HTTP health & endpoints ---
app = Flask(__name__)


@app.get("/health")
def health():
    age = int(time.time()) - int(last_tick_ts or 0)
    return jsonify(
        status="ok" if age < DATA_STALL_SEC * 2 else "stale",
        age_sec=age,
        symbols=len(klines),
    )


@app.get("/top5")
def top5():
    gains, losses = compute_top5()
    if gains is None:
        return jsonify(error="no data yet"), 503
    return jsonify(
        ts=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        top5_gainers=gains.to_dict(orient="records"),
        top5_losers=losses.to_dict(orient="records"),
    )


def http_run():
    port = int(os.getenv("WS_SCREENER_PORT", "8000"))
    app.run(host="0.0.0.0", port=port)


def get_contract_symbols():
    wl = os.getenv("SYMBOL_WHITELIST", "").strip()
    if wl:
        return [s.strip() for s in wl.split(",") if s.strip()]
    try:
        r = requests.get(f"{REST_BASE}/api/v1/contract/detail", timeout=10)
        data = (r.json() or {}).get("data") or []
        out = sorted({it.get("symbol") for it in data if it.get("symbol")})
        return out or ["BTC_USDT", "ETH_USDT", "SOL_USDT", "XRP_USDT", "LTC_USDT"]
    except Exception:
        return ["BTC_USDT", "ETH_USDT", "SOL_USDT", "XRP_USDT", "LTC_USDT"]


def on_message(ws, message):
    global last_tick_ts
    try:
        msg = json.loads(message)
    except (json.JSONDecodeError, Exception):
        return
    if msg.get("channel") == "push.kline":
        d = msg.get("data", {})
        if d.get("interval") != KL_INTERVAL:
            return
        s = d.get("symbol")
        c = d.get("c")
        ts = d.get("t")
        v = d.get("vol")
        if s and c is not None and ts:
            try:
                price = float(c)
                timestamp = int(ts)
                volume = float(v) if v else 0.0

                # Kline speichern
                klines[s].append((timestamp, price))
                last_tick_ts = int(time.time())

                # Pct_change berechnen (falls genug Daten)
                if redis_client and len(klines[s]) >= 2:
                    first_price = klines[s][0][1]
                    pct_change = ((price - first_price) / first_price) * 100.0

                    # market_data Event publishen
                    event = {
                        "type": "market_data",
                        "symbol": s,
                        "timestamp": timestamp,
                        "price": price,
                        "volume": volume,
                        "pct_change": round(pct_change, 3),
                        "interval": "1m",
                    }
                    try:
                        redis_client.publish("market_data", json.dumps(event))
                    except Exception as e:
                        print(f"Redis publish fehler: {e}", file=sys.stderr)
            except Exception as e:
                print(f"on_message fehler: {e}", file=sys.stderr)


def on_open(ws, chunk):
    for s in chunk:
        sub = {
            "method": "sub.kline",
            "param": {
                "symbol": s,
                "interval": KL_INTERVAL,
            }
        }
        ws.send(json.dumps(sub))
        time.sleep(0.005)


def on_error(ws, error):
    print(f"[WS ERROR] {error}", file=sys.stderr)


def on_close(ws, close_status_code, close_msg):
    print(f"[WS CLOSE] Code={close_status_code}, Msg={close_msg}", file=sys.stderr)


def make_ws(chunk):
    return WebSocketApp(
        WS_URL,
        on_message=on_message,
        on_open=lambda ws: on_open(ws, chunk),
        on_error=on_error,
        on_close=on_close,
    )


def ws_worker(chunk):
    backoff = 1.0
    reconnect_count = 0
    while True:
        try:
            reconnect_count += 1
            print(f"[WS] Connecting chunk (attempt {reconnect_count})...", file=sys.stderr)
            ws = make_ws(chunk)
            ws.run_forever()
            print(f"[WS] Disconnected (attempt {reconnect_count})", file=sys.stderr)
        except Exception as e:
            print(f"[WS ERROR] Chunk reconnect #{reconnect_count}: {e}", file=sys.stderr)
        time.sleep(backoff)
        backoff = min(backoff * 2.0, 30.0)


def chunkify(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def compute_top5():
    rows = []
    for s, dq in klines.items():
        if len(dq) < 2:
            continue
        first = dq[0][1]
        last = dq[-1][1]
        pct = (last - first) / first * 100.0
        rows.append({"symbol": s, "pct_change": round(pct, 3)})
    if not rows:
        return None, None
    df = pd.DataFrame(rows)
    return (
        df.sort_values("pct_change", ascending=False).head(5),
        df.sort_values("pct_change", ascending=True).head(5),
    )


def printer():
    while True:
        time.sleep(15)
        gains, losses = compute_top5()
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"\n[{ts}] Top movers ({LOOKBACK_MIN}m):")
        if gains is None:
            print("Noch keine Daten – warte auf Klines...")
        else:
            print("TOP 5 Gewinner:")
            print(gains.to_string(index=False))
            print("TOP 5 Verlierer:")
            print(losses.to_string(index=False))


if __name__ == "__main__":
    print("Hole Symbolliste...")
    symbols = get_contract_symbols()
    # Start HTTP
    threading.Thread(target=http_run, daemon=True).start()
    # WS in Chunks (200 pro Verbindung)
    for ch in chunkify(symbols, 200):
        threading.Thread(target=ws_worker, args=(ch,), daemon=True).start()
        time.sleep(0.2)
    # Console printer
    printer()
