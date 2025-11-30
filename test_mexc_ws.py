#!/usr/bin/env python3
"""
Test-Script um MEXC WebSocket zu verifizieren.
Testet ob WebSocket connected und Kline-Daten empfängt.
"""
import json
import time
from websocket import WebSocketApp

WS_URL = "wss://contract.mexc.com/ws"
TEST_SYMBOLS = ["BTC_USDT", "ETH_USDT"]
received_messages = []


def on_message(ws, message):
    try:
        msg = json.loads(message)
        received_messages.append(msg)
        print(f"[MESSAGE] {json.dumps(msg, indent=2)}")
    except Exception as e:
        print(f"[ERROR] Message parse: {e}")


def on_error(ws, error):
    print(f"[WS ERROR] {error}")


def on_close(ws, close_status_code, close_msg):
    print(f"[WS CLOSED] Code: {close_status_code}, Msg: {close_msg}")


def on_open(ws):
    print("[WS OPEN] Connected successfully!")
    # Subscribe to BTC and ETH klines
    for symbol in TEST_SYMBOLS:
        sub = {
            "op": "sub",
            "channel": "sub.kline",
            "symbol": symbol,
            "interval": "Min1",
        }
        print(f"[SUBSCRIBE] {json.dumps(sub)}")
        ws.send(json.dumps(sub))
        time.sleep(0.1)


if __name__ == "__main__":
    print(f"Testing MEXC WebSocket: {WS_URL}")
    print("Will run for 30 seconds and print all messages...")

    ws = WebSocketApp(
        WS_URL,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open,
    )

    # Run for 30 seconds
    import threading

    ws_thread = threading.Thread(target=ws.run_forever, daemon=True)
    ws_thread.start()

    time.sleep(30)
    ws.close()

    print("\n=== RESULTS ===")
    print(f"Total messages received: {len(received_messages)}")
    if received_messages:
        print("Sample messages:")
        for msg in received_messages[:3]:
            print(json.dumps(msg, indent=2))
    else:
        print("❌ NO MESSAGES RECEIVED - WebSocket might be broken!")
