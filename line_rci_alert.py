#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
line_rci_alert.py
  ・モチポヨ方式の RCI シグナルを監視
  ・ヒットしたら LINE に通知
  ────────────────────────────────
  ● Render では
      Flask アプリ（webhook_receiver.py）から
      loop_forever() がバックグラウンドで起動
  ● GitHub Actions では
      1 回だけ実行して即終了（one_shot モード）
"""

from __future__ import annotations
import os, json, time
from pathlib import Path
from typing import Optional

import requests
import numpy  as np
import pandas as pd
import yfinance as yf


# ────────────────────────────────
# LINE 関連（小文字の環境変数で統一）
# ────────────────────────────────
LINE_TOKEN = os.getenv("line_channel_access_token")
LINE_USER  = os.getenv("line_user_id")

def send_line(text: str) -> None:
    """LINE プッシュメッセージ"""
    url  = "https://api.line.me/v2/bot/message/push"
    hdrs = {"Authorization": f"Bearer {LINE_TOKEN}",
            "Content-Type":  "application/json"}
    body = {"to": LINE_USER,
            "messages": [{"type": "text", "text": text}]}

    res = requests.post(url, headers=hdrs, json=body, timeout=10)
    print("📤 LINE status:", res.status_code, flush=True)


# ────────────────────────────────
# RCI & モチポヨ判定
# ────────────────────────────────
def rci(series: pd.Series, n: int) -> float:
    if len(series) < n:
        return np.nan
    date_rank  = np.arange(1, n + 1)
    price_rank = series.tail(n).rank(method="first").values
    d = date_rank - price_rank
    return (1 - 6 * np.sum(d ** 2) / (n * (n**2 - 1))) * 100


def mochipoyo(df: pd.DataFrame, cfg: dict) -> Optional[str]:
    r9, r26, r52 = (rci(df["Close"], 9),
                    rci(df["Close"], 26),
                    rci(df["Close"], 52))
    hi           = cfg["rci9"]
    lo1, lo2     = cfg["rci26_min"], cfg["rci26_max"]

    if r9 >  hi and lo1 <= r26 <= lo2 and r52 <  0:
        return "SELL"
    if r9 < -hi and -lo2 <= r26 <= -lo1 and r52 > 0:
        return "BUY"
    return None


# ────────────────────────────────
# 設定読込み
# ────────────────────────────────
def load_cfg(path: str = "config.json") -> dict:
    cfg_path = Path(__file__).with_name(path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"[設定ファイル] {cfg_path} が見つかりません")
    return json.loads(cfg_path.read_text(encoding="utf-8"))


# ────────────────────────────────
# 1 回だけ判定
# ────────────────────────────────
def one_shot(cfg: dict) -> None:
    for name, ticker in cfg["pairs"].items():
        df = yf.download(ticker, interval="1m", period="1d", progress=False)
        if df.empty:
            print(f"{name}: データ取得失敗");  continue

        sig = mochipoyo(df, cfg["mochipoyo"])
        if sig:
            price = df["Close"].iloc[-1]
            text  = f"📈 {name} モチポヨシグナル!!\n種別: {sig}\n価格: {price}"
            print(text, flush=True)
            send_line(text)
        else:
            print(f"{name}: シグナルなし")


# ────────────────────────────────
# 常駐ループ （Flask から呼び出す）
# ────────────────────────────────
def loop_forever(path: str = "config.json") -> None:
    cfg = load_cfg(path)
    while True:
        one_shot(cfg)
        time.sleep(60)          # 1 分ごと


# ────────────────────────────────
# エントリーポイント
# ────────────────────────────────
if __name__ == "__main__":
    print("✅ line_rci_alert 起動",
          "TOKEN:", "OK" if LINE_TOKEN else "None",
          "USER:",  LINE_USER, flush=True)

    # GitHub Actions なら環境変数が true なので one_shot だけ
    if os.getenv("GITHUB_ACTIONS") == "true":
        one_shot(load_cfg())
    else:
        loop_forever()
