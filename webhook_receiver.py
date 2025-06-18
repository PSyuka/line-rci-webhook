from flask import Flask, request
import json
import requests

app = Flask(__name__)

LINE_ACCESS_TOKEN = 'jypU1wjnvlCWmxCu2MJr+xygYyWQsU/4BKol+Lj4ynnEbOuuC6J2/Jsp61ZqxBsTSqFl46B5WP+Ie/5R3q/p0/vPie3svaTDmF2nHJXydM+PlbhtC3sAhzsuugCP9J18MbI4HPKixhAD3sGyrjsTkAdB04t89/1O/w1cDnyilFU='

def send_line_message(to, message):
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_ACCESS_TOKEN}'
    }
    data = {
        'to': to,
        'messages': [{
            'type': 'text',
            'text': message
        }]
    }
    response = requests.post(url, headers=headers, json=data)
    print(f'送信ステータス: {response.status_code}', flush=True)

@app.route("/webhook", methods=['POST'])
def webhook():
    body = request.get_json()
    print("📦 受信データ：", json.dumps(body, indent=2, ensure_ascii=False), flush=True)

    events = body.get("events", [])
    for event in events:
        if event["type"] == "message":
            user_id = event["source"]["userId"]
            print(f"📌 userId取得: {user_id}", flush=True)
            send_line_message(user_id, "📢 RCI通知テスト：WebhookからLINE通知成功！")
    return "OK", 200

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
