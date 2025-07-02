#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
line_rci_alert.py
  モチポヨ方式の RCI アラートを LINE に送信するスクリプト
  ・Render 上では常駐ループ
  ・GitHub Actions では 1 回だけ実行して即終了
"""

from __future__ import annotations
import os, json, time
from pathlib import Path
from typing import Optional

import requests
import numpy as np
import pandas as pd
import yfinance as yf


# ────────────────────────────────
# LINE 設定（Secrets で小文字に）
# ────────────────────────────────
LINE_TOKEN = os.getenv("line_channel_access_token")
LINE_USER  = os.getenv("line_user_id")

def send_line(msg: str) -> None:
    """プッシュメッセージを送信"""
    url = "https://api.line.me/v2/bot/message/push"
    hdr = {"Authorization": f"Bearer {LINE_TOKEN}", "Content-Type": "application/json"}
    body = {"to": LINE_USER, "messages": [{"type": "text", "text": msg}]}
    res = requests.post(url, headers=hdr, json=body, timeout=10)
    print("📤 LINE status:", res.status_code, flush=True)


# ────────────────────────────────
# RCI & モチポヨ判定
# ────────────────────────────────
def rci(s: pd.Series, n: int) -> float:
    if len(s) < n:
        return np.nan
    date_rank  = np.arange(1, n + 1)
    price_rank = s.tail(n).rank(method="first").values
    d = date_rank - price_rank
    return (1 - 6 * np.sum(d ** 2) / (n * (n**2 - 1))) * 100


def mochipoyo(df: pd.DataFrame, cfg: dict) -> Optional[str]:
    r9, r26, r52 = (rci(df["Close"], 9), rci(df["Close"], 26), rci(df["Close"], 52))
    hi          = cfg["rci9"]
    lo1, lo2    = cfg["rci26_min"], cfg["rci26_max"]

    if r9 >  hi and lo1 <= r26 <= lo2 and r52 <  0:
        return "SELL"
    if r9 < -hi and -lo2 <= r26 <= -lo1 and r52 > 0:
        return "BUY"
    return None


# ────────────────────────────────
# 設定ファイル読込み
# ────────────────────────────────
def load_cfg(fname: str = "config.json") -> dict:
    here = Path(__file__).resolve().parent
    cfg_path = here / fname
    if not cfg_path.exists():
        raise FileNotFoundError(f"[設定] {cfg_path} が見つかりません")
    return json.loads(cfg_path.read_text(encoding="utf-8"))


# ────────────────────────────────
# メイン処理
# ────────────────────────────────
def one_shot(cfg: dict) -> None:
    """1 回だけ判定して結果があれば通知"""
    for name, ticker in cfg["pairs"].items():
        df = yf.download(ticker, interval="1m", period="1d", progress=False)
        if df.empty:
            print(f"{name}: データ取得失敗")
            continue

        sig = mochipoyo(df, cfg["mochipoyo"])
        if sig:
            price = df["Close"].iloc[-1]
            msg = f"📈 {name} でモチポヨシグナル！\n種別: **{sig}**\n価格: {price}"
            print(msg, flush=True)
            send_line(msg)
        else:
            print(f"{name}: シグナルなし")


def main() -> None:
    cfg = load_cfg()

    # ─ GitHub Actions なら 1 回だけ実行して終了 ─
    if os.getenv("GITHUB_ACTIONS") == "true":
        one_shot(cfg)
        return

    # ─ Render (常駐) ─
    while True:
        one_shot(cfg)
        time.sleep(60)           # 1 分間隔


if __name__ == "__main__":
    print("✅ line_rci_alert 起動",
          "TOKEN:", "OK" if LINE_TOKEN else "None",
          "USER:",  LINE_USER, flush=True)
    main()
