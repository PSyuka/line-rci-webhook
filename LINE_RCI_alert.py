import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time

# LINE通知の設定
LINE_NOTIFY_TOKEN = "jypU1wjnvlCWmxCu2MJr+xygYyWQsU/4BKol+Lj4ynnEbOuuC6J2/Jsp61ZqxBsTSqFl46B5WP+Ie/5R3q/p0/vPie3svaTDmF2nHJXydM+PlbhtC3sAhzsuugCP9J18MbI4HPKixhAD3sGyrjsTkAdB04t89/1O/w1cDnyilFU="
LINE_NOTIFY_URL = "https://notify-api.line.me/api/notify"

def send_line_message(message):
    headers = {
        "Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"
    }
    data = {"message": message}
    requests.post(LINE_NOTIFY_URL, headers=headers, data=data)

# RCI計算関数
def calculate_rci(series, period):
    if len(series) < period:
        return np.nan
    date_rank = np.arange(1, period + 1)
    price_rank = series.tail(period).rank(method='first').values
    d = date_rank - price_rank
    rci = 1 - (6 * np.sum(d ** 2)) / (period * (period ** 2 - 1))
    return rci * 100

# 売買判定関数（もちぽよ式）
def check_mochipoyo_condition(df):
    rci9 = calculate_rci(df['Close'], 9)
    rci26 = calculate_rci(df['Close'], 26)
    rci52 = calculate_rci(df['Close'], 52)

    if rci9 > 80 and rci26 <= 0 and rci26 >= -80 and rci52 < 0:
        return "SELL"
    elif rci9 < -80 and rci26 >= 0 and rci26 <= 80 and rci52 > 0:
        return "BUY"
    return None

# 通貨とティッカー対応
tickers = {
    "USDJPY": "JPY=X",
    "EURJPY": "EURJPY=X",
    "GBPJPY": "GBPJPY=X"
}

# メイン処理
def main():
    while True:
        for pair, ticker in tickers.items():
            df = yf.download(ticker, interval="1m", period="1d")
            if df.empty:
                continue
            signal = check_mochipoyo_condition(df)
            if signal:
                msg = f"{pair}でシグナル検出！条件: {signal}\n価格: {df['Close'].iloc[-1]}"
                print(msg)
                send_line_message(msg)
        time.sleep(60)

if __name__ == "__main__":
    main()
