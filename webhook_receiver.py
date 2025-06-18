from flask import Flask, request
import json

app = Flask(__name__)

@app.route("/webhook", methods=['POST'])
def webhook():
    body = request.get_json()
    print("📦 受信データ：", json.dumps(body, indent=2, ensure_ascii=False))  # ← ここ追加！
    
    events = body.get("events", [])
    for event in events:
        if event["type"] == "message":
            user_id = event["source"]["userId"]
            print(f"📌 userId取得: {user_id}")
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
