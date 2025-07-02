import os, json, time
import requests, numpy as np, pandas as pd, yfinance as yf

# ---- LINE ----------------------------------------------------------------
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER  = os.getenv("LINE_USER_ID")

def send_line(msg: str):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Authorization": f"Bearer {LINE_TOKEN}",
               "Content-Type": "application/json"}
    body = {"to": LINE_USER,
            "messages": [{"type": "text", "text": msg}]}
    r = requests.post(url, headers=headers, json=body)
    print("📤 LINE status:", r.status_code, flush=True)

# ---- モチポヨ判定 --------------------------------------------------------
def rci(series: pd.Series, period: int) -> float:
    if len(series) < period: return np.nan
    date_rank  = np.arange(1, period + 1)
    price_rank = series.tail(period).rank(method="first").values
    d = date_rank - price_rank
    return (1 - 6 * np.sum(d ** 2) / (period * (period**2 - 1))) * 100

def mochipoyo(df: pd.DataFrame, cfg) -> str | None:
    rci9, rci26, rci52 = (
        rci(df["Close"], 9),
        rci(df["Close"], 26),
        rci(df["Close"], 52),
    )
    hi  = cfg["rci9"]
    lo1, lo2 = cfg["rci26_min"], cfg["rci26_max"]

    if rci9 >  hi and lo1 <= rci26 <= lo2 and rci52 <  0:
        return "SELL"
    if rci9 < -hi and -lo2 <= rci26 <= -lo1 and rci52 > 0:
        return "BUY"
    return None

# ---- メインループ --------------------------------------------------------
def load_cfg(path="config.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    cfg = load_cfg()
    pairs = cfg["pairs"]
    thresh = cfg["mochipoyo"]

    while True:
        for name, ticker in pairs.items():
            df = yf.download(ticker, interval="1m", period="1d", progress=False)
            if df.empty:
                print(f"{name}: データ取得失敗")
                continue

            sig = mochipoyo(df, thresh)
            if sig:
                price = df["Close"].iloc[-1]
                msg = f"📈 {name} でモチポヨシグナル！\n種別: **{sig}**\n価格: {price}"
                print(msg)
                send_line(msg)
        time.sleep(60)          # 1 分おきに実行

if __name__ == "__main__":
    # 環境変数が取れているか確認
    print("✅ line_rci_alert 起動",
          "TOKEN:", "OK" if LINE_TOKEN else "None",
          "USER:",  LINE_USER, flush=True)
    main()
