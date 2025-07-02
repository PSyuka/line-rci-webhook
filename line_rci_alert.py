#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
line_rci_alert.py
  ・yfinance で 1分足を取得（Tickless になると None が返るので guard 付き）
  ・もちぽよ式の BUY / SELL シグナル検出
  ・LINE Messaging API へプッシュ
"""

from __future__ import annotations
import os, json, time, requests, numpy as np, pandas as pd, yfinance as yf
from typing import Dict, Optional

# ── 1) Secrets（小文字！）──────────────────────────────
TOKEN   = os.getenv("line_channel_access_token")   # Bearer token
USER_ID = os.getenv("line_user_id")                # プッシュ先 userId

if not TOKEN or not USER_ID:                     # 起動直後のロギング
    raise RuntimeError("環境変数 line_channel_access_token / line_user_id が設定されていません")

print("✅ スクリプト起動 OK")

# ── 2) 設定ファイル ──────────────────────────────────
CFG_PATH = os.getenv("config_file", "config.json")

with open(CFG_PATH, encoding="utf-8") as f:
    CFG: Dict = json.load(f)

PAIRS: Dict[str, str] = CFG["pairs"]             # 表示名 → yfinance ティッカー
THR   : Dict       = CFG["mochipoyo"]            # 閾値セット

# ── 3) 送信関数（LINE→Discord 差し替えはここだけ）─────────
def push(msg: str) -> None:
    res = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json"
        },
        json={"to": USER_ID, "messages": [{"type": "text", "text": msg}]},
        timeout=10
    )
    print("LINE status", res.status_code)

# ── 4) RCI 関連ロジック ──────────────────────────────
def rci(series: pd.Series, n: int) -> float:
    if len(series) < n:
        return np.nan
    rank_date  = np.arange(1, n + 1)
    rank_price = series.tail(n).rank(method="first").values
    d = rank_date - rank_price
    return (1 - 6 * np.sum(d ** 2) / (n * (n ** 2 - 1))) * 100

def mochipoyo(df: pd.DataFrame) -> Optional[str]:
    r9, r26, r52 = (rci(df["Close"], n) for n in (9, 26, 52))

    if (
        r9  >  THR["rci9"]
        and THR["rci26_min"] <= r26 <= THR["rci26_max"]
        and r52 < 0
    ):
        return "SELL"
    elif (
        r9  < -THR["rci9"]
        and -THR["rci26_max"] <= r26 <= -THR["rci26_min"]
        and r52 > 0
    ):
        return "BUY"
    return None

# ── 5) メインループ（GitHub Actions では 1 回で終了）────────
def main() -> None:
    for name, ticker in PAIRS.items():
        df = yf.download(ticker, interval="1m", period="1d", progress=False)
        if df.empty:
            print(name, "データ取得失敗")
            continue

        sig = mochipoyo(df)
        if sig:
            price = df["Close"].iloc[-1]
            msg = f"{name}: {sig} 価格={price:.4f}"
            push(msg)
            print("▶", msg)
        else:
            print(name, "シグナルなし")

if __name__ == "__main__":
    # GitHub Actions なら 1 回実行して終了
    # Render で「毎分」動かす場合は while ループ＋sleep(60) にする
    LOOP = os.getenv("continuous", "false").lower() == "true"
    while True:
        main()
        if not LOOP:
            break
        time.sleep(60)
