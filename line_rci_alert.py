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
    if len(s) < n:
        return np.nan
    date_rank  = np.arange(1, n + 1)
    price_rank = s.tail(n).rank(method="first").to_numpy()
    d = date_rank - price_rank
    return (1 - 6 * np.sum(d**2) / (n * (n**2 - 1))) * 100

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
        if len(df) < 52:
            print(f"{name}: データ本数が足りません ({len(df)})");  continue

        # 直近値と RCI を数値で取得
        close_col = df["Close"]
        if isinstance(close_col, pd.DataFrame):          # Multi-Index 対応
            close_col = close_col.iloc[:, 0]             # 1列目を Series に
        price = float(close_col.iat[-1])                 # これで OK
        r9, r26, r52 = (rci(df["Close"], 9),
                        rci(df["Close"], 26),
                        rci(df["Close"], 52))

        print(f"{name:<6} price={price:>7.3f}  "
              f"R9={r9:>6.1f}  R26={r26:>6.1f}  R52={r52:>6.1f}",
              flush=True)

        sig = mochipoyo(df, cfg["mochipoyo"])
        if sig:
            msg = (f"📈 {name} モチポヨシグナル\n"
                   f"種別: **{sig}**\n価格: {price}")
            send_line(msg)

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
