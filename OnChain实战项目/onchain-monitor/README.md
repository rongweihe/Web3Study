# 区块链链上监控系统 (Chain Monitor MVP)

本项目是一个基于 **Go + Python + HTML** 的链上监控系统，具备以下功能：
- 主流币价格展示（BTC、ETH、SOL、BNB、OKB、BGB）
- ETH 大额转账检测（>100 ETH）
- 飞书告警机器人通知
- 系统资源监控展示
- 投资金句随机展示

### 🚀 一键启动（MacOS）

```bash
chmod +x build.sh
./build.sh
```

浏览器访问: http://localhost:8080

###  📁项目说明

- Go：后端 API + 数据聚合

- Python：ETH 大额转账监控 & 飞书通知

- HTML/CSS/JS：前端展示（实时刷新）

```yaml

---

### `build.sh`
```bash
#!/bin/bash
echo "🚀 启动 Chain Monitor MVP ..."
export PORT=8080

# 启动 ETH 监控脚本
echo "▶ 启动 Python ETHScan 监控 ..."
python3 scripts/ethscan_monitor.py &

# 启动 Go 后端
echo "▶ 启动 Go 服务 ..."
go run cmd/main.go

```