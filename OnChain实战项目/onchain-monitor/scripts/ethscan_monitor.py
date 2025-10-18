import requests
import time
import json
import os

API_TOKEN = "FX6PB88QGVUWAFZYQ1V2EGKAM5WREPFFDX"
API_URL = f"https://api.etherscan.io/v2/api?chainid=1&module=account&action=txlist&address=0x742d35Cc6634C0532925a3b844Bc454e4438f44e&sort=desc&apikey={API_TOKEN}"
OUT_FILE = "data/eth_top.json"

def fetch_large_transfers():
    try:
        resp = requests.get(API_URL)
        data = resp.json()
        if data.get("status") != "1":
            print("无有效交易数据")
            return []

        txs = data.get("result", [])
        large_txs = []
        for tx in txs:
            value_eth = int(tx["value"]) / 1e18
            if value_eth >= 100:
                large_txs.append({
                    "from": tx["from"],
                    "to": tx["to"],
                    "amount": value_eth,
                    "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(tx["timeStamp"])))
                })

        # 排序取 Top5
        large_txs.sort(key=lambda x: x["amount"], reverse=True)
        top5 = large_txs[:5]

        # 保存到文件
        os.makedirs("data", exist_ok=True)
        with open(OUT_FILE, "w") as f:
            json.dump(top5, f, indent=2)

        print(f"✅ 更新 Top5 ETH 转账 {len(top5)} 条记录")
        return top5

    except Exception as e:
        print("监控异常:", e)
        return []

if __name__ == "__main__":
    while True:
        fetch_large_transfers()
        time.sleep(10)
