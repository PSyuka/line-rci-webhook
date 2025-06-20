import os
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time

# Secretsから取得
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")

def send_line_message(user_id, message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    data = {
        "to": user_id,
        "messages": [{
            "type": "text",
            "text": message
        }]
    }
    resp = requests.post(url, headers=headers, json=data)
    print("LINE送信ステータス:", resp.status_code)

def calculate_rci(series, period):
    if len(series) < period:
        return np.nan
    date_rank = np.arange(1, period + 1)
    price_rank = series.tail(period).rank(method='first').values
    d = date_rank - price_rank
    rci = 1 - (6 * np.sum(d ** 2)) / (period * (period ** 2 - 1))
    return rci * 100

def check_mochipoyo_condition(df):
    rci9 = calculate_rci(df['Close'], 9)
    rci26 = calculate_rci(df['Close'], 26)
    rci52 = calculate_rci(df['Close'], 52)

    if rci9 > 80 and -80 <= rci26 <= 0 and rci52 < 0:
        return "SELL"
    elif rci9 < -80 and 0 <= rci26 <= 80 and rci52 > 0:
        return "BUY"
    return None

tickers = {
    "USDJPY": "JPY=X",
    "EURJPY": "EURJPY=X",
    "GBPJPY": "GBPJPY=X"
}

def main():
    for pair, ticker in tickers.items():
        df = yf.download(ticker, interval="1m", period="1d")
        if df.empty:
            continue
        signal = check_mochipoyo_condition(df)
        if signal:
            msg = f"{pair}でシグナル検出！条件: {signal}\n価格: {df['Close'].iloc[-1]}"
            print(msg)
            send_line_message(LINE_USER_ID, msg)

if __name__ == "__main__":
    main()
