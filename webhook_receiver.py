#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
webhook_receiver.py
  LINE Messaging API Webhook 受信 & エコー返信
  初回リクエスト時にモチポヨ監視ループをバックグラウンド起動
"""

from flask import Flask, request
import json, os, requests
from threading import Thread

from line_rci_alert import loop_forever   # ← 監視ループをインポート

# ────────────────────────────────
# LINE 設定
# ────────────────────────────────
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

def push(to: str, text: str) -> None:
    url  = "https://api.line.me/v2/bot/message/push"
    hdrs = {"Authorization": f"Bearer {LINE_TOKEN}",
            "Content-Type":  "application/json"}
    body = {"to": to, "messages": [{"type": "text", "text": text}]}
    r = requests.post(url, headers=hdrs, json=body, timeout=10)
    print("📤 LINE status:", r.status_code, flush=True)


# ────────────────────────────────
# Flask アプリ
# ────────────────────────────────
app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    body = request.get_json()
    print("📩 webhook:", json.dumps(body, ensure_ascii=False), flush=True)

    for ev in body.get("events", []):
        if ev["type"] == "message":
            uid = ev["source"]["userId"]
            push(uid, "📢 RCI通知テスト：Webhookから LINE 通知成功！")
    return "OK", 200


@app.before_first_request
def _start_loop():
    """最初のリクエストを受けたら監視ループを起動"""
    Thread(target=loop_forever, daemon=True).start()
    print("🔁 モチポヨ監視ループを開始", flush=True)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
