#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
line_rci_alert.py – モチポヨ方式 RCI 監視 & LINE 通知
  * Render 上では loop_forever() を webhook_receiver から起動
  * GitHub Actions では one_shot() だけ呼ばれて終了
"""

from __future__ import annotations
import os, json, time
from pathlib import Path
from typing import Optional

import requests, numpy as np, pandas as pd, yfinance as yf

# ─── LINE ────────────────────────────────────────────────────────────────
LINE_TOKEN = os.getenv("line_channel_access_token")
LINE_USER  = os.getenv("line_user_id")

def send_line(text: str) -> None:
    url  = "https://api.line.me/v2/bot/message/push"
    hdrs = {"Authorization": f"Bearer {LINE_TOKEN}",
            "Content-Type":  "application/json"}
    body = {"to": LINE_USER, "messages": [{"type": "text", "text": text}]}
    r = requests.post(url, headers=hdrs, json=body, timeout=10)
    print("📤 LINE status:", r.status_code, flush=True)

# ─── RCI & モチポヨ判定 ───────────────────────────────────────────────
def rci(s: pd.Series, n: int) -> float:
    """n 本分の RCI を −100〜100 で返す"""
    if len(s) < n:
        return np.nan

    # ── 修正ポイント ─────────────────────────────
    closes = s.tail(n).reset_index(drop=True)            # ← index を振り直す
    price_rank = closes.rank(method="first").to_numpy()  # 1〜n の順位になる
    # ────────────────────────────────────────────

    date_rank = np.arange(1, n + 1)                      # 1,2,…,n
    d = date_rank - price_rank
    return (1 - 6 * (d**2).sum() / (n * (n**2 - 1))) * 100


def mochipoyo(df: pd.DataFrame, cfg: dict) -> Optional[str]:
    r9, r26, r52 = (rci(df["Close"], 9),
                    rci(df["Close"], 26),
                    rci(df["Close"], 52))
    hi = cfg["rci9"]; lo1, lo2 = cfg["rci26_min"], cfg["rci26_max"]
    if r9 >  hi and lo1 <= r26 <= lo2 and r52 <  0: return "SELL"
    if r9 < -hi and -lo2 <= r26 <= -lo1 and r52 > 0: return "BUY"
    return None

# ─── 設定 ────────────────────────────────────────────────────────────────
def load_cfg(path="config.json") -> dict:
    fp = Path(__file__).with_name(path)
    if not fp.exists():
        raise FileNotFoundError(f"[設定] {fp} が見つかりません")
    return json.loads(fp.read_text(encoding="utf-8"))

# ─── 1 回だけ判定 ────────────────────────────────────────────────────
def one_shot(cfg: dict) -> None:
    for name, ticker in cfg["pairs"].items():
        df = yf.download(ticker, interval="1m", period="2d", progress=False)

        # ─ 本数不足ならスキップ ─
        if len(df) < 52:
            print(f"{name}: {len(df)} 本しかないのでスキップ");  continue

        # デバッグ表示用
        price = float(df["Close"].iat[-1])
        r9  = rci(df["Close"], 9)
        r26 = rci(df["Close"], 26)
        r52 = rci(df["Close"], 52)
        print(f"{name} price={price:.3f}  R9={r9:6.1f}  R26={r26:6.1f}  R52={r52:6.1f}")

        sig = mochipoyo(df, cfg["mochipoyo"])
        if sig:
            send_line(f"📈 {name} でモチポヨシグナル！\n種別: {sig}\n価格: {price}")


# ─── 常駐ループ（Render 用）───────────────────────────────────────────
def loop_forever(path="config.json") -> None:
    cfg = load_cfg(path)
    while True:
        one_shot(cfg)
        time.sleep(60)

# ─── エントリーポイント ──────────────────────────────────────────────
if __name__ == "__main__":
    print("✅ line_rci_alert 起動",
          "TOKEN:", "OK" if LINE_TOKEN else "None",
          "USER:", LINE_USER, flush=True)

    if os.getenv("GITHUB_ACTIONS") == "true":
        one_shot(load_cfg())
    else:
        loop_forever()
