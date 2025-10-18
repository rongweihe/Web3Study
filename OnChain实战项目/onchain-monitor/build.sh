#!/bin/bash
echo "🚀 启动 Chain Monitor MVP ..."
export PORT=8080

# 启动 ETH 监控脚本
echo "▶ 启动 Python ETHScan 监控 ..."
python3 scripts/ethscan_monitor.py &

# 启动 Go 后端
echo "▶ 启动 Go 服务 ..."
go run cmd/main.go
