import requests, time, json, os

API_TOKEN = "You API TOKEN KEY"
THRESHOLD = 100
URL = f"https://api.etherscan.io/v2/api?chainid=1&module=account&action=txlist&address=0x742d35Cc6634C0532925a3b844Bc454e4438f44e&sort=desc&apikey={API_TOKEN}"

# https://api.etherscan.io/v2/api?chainid=1&module=account&action=txlist&address=0xddbd2b932c763ba5b1b7ae3b362eac3e8d40121a&startblock=0&endblock=99999999&sort=asc&apikey=FX6PB88QGVUWAFZYQ1V2EGKAM5WREPFFDX

def send_feishu_alert(msg):
    hook = os.getenv("FEISHU_BOT_WEBHOOK", "")
    if not hook:
        print("[WARN] 未配置 FEISHU_BOT_WEBHOOK")
        return
    requests.post(hook, json={"msg_type": "text", "content": {"text": msg}})

def monitor_loop():
    print("ETH 大额转账监控启动中 ...")
    while True:
        try:
            res = requests.get(URL)
            data = res.json().get("result", [])
            for tx in data[:20]:
                val = int(tx["value"]) / 1e18
                if val > THRESHOLD:
                    msg = f"⚠️ 检测到大额转账: {val:.2f} ETH, 地址: {tx['from']} -> {tx['to']}"
                    print(msg)
                    send_feishu_alert(msg)
            time.sleep(30)
        except Exception as e:
            print("监控异常:", e)
            time.sleep(60)

if __name__ == "__main__":
    monitor_loop()
