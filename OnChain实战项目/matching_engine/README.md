## 项目简介

- 基于 Go 开发的高性能撮合引擎

## 架构（MVP版）

目标：内存撮合，限价单、撤单、连续竞价；多标的（symbol）；可开关交易 ；进程重启之后可恢复；结果实时下发；

## 组件分层
- API 层（Gateway）：HTTP/gRPC 接单和撤单 -》 写入 Kafka「指令流」；只做校验和限流，不直接写库；
- 撮合层（MatcherWorkers）:每个 symbol 一个 goroutine，订阅管理 symbol 的顺序化指令流（Kafka 分区），在内存维护 OrderBook，撮合成交形成事件
- 事件下发（Fanout）：撮合产生的 Execution/ACK/Reject 事件 -> 「事件流」；由推送服务给到用户（WebSocket）或给清结算系统。
- 持久化层：
- - WAL：
- - 快照：
- - 落库：
- 运维和控制：控制面（Control Plane）可以发「暂停/恢复 symbol」的管理指令（走独立 Kafka 主题或管理 API），撮合协程按指令切换状态。

## 核心时序
- 下单：client → API → Kafka(order_cmds.<symbol>) → Matcher(symbol) → 生成 ack/reject + trades → Kafka(order_events.<symbol>) → 推送 & 异步落库。
- 撤单：同上，指令类型变更。
- 重启恢复：Matcher 启动 → 读 Redis 快照（含上次快照 offset）→ 从 Kafka(offset+1) 继续回放 → 恢复到最新 → 开始撮合。

## 代码结构

```go
matching_engine/
├── cmd/
│   ├── api-gateway/            # HTTP/gRPC 接口服务（接单、撤单、查询）
│   ├── matcher/                # 撮合进程（可多实例；symbol→partition）
│   └── fanout/                 # 事件下发（ws/kafka→ws）
├── internal/
│   ├── book/
│   │   ├── order.go            # Order, enums
│   │   ├── level.go            # Level 队列
│   │   ├── orderbook.go        # 买卖盘、撮合核心
│   │   └── snapshot.go         # 快照序列化/反序列化
│   ├── engine/
│   │   ├── matcher.go          # 每symbol goroutine，消费cmds，产出events
│   │   ├── controller.go       # 开关 symbol，模式控制
│   │   └── sequencer.go        # 序列号与事件构造
│   ├── io/
│   │   ├── kafka_consumer.go
│   │   ├── kafka_producer.go
│   │   ├── redis_store.go
│   │   └── mysql_repo.go
│   ├── api/
│   │   ├── http.go             # /orders/new, /orders/cancel, /symbols/open|close
│   │   └── ws.go               # 事件订阅
│   ├── types/
│   │   ├── cmd.go              # OrderCommand
│   │   └── event.go            # OrderEvent
│   ├── config/
│   │   └── config.go
│   └── metrics/
│       └── prometheus.go
├── pkg/
│   └── decimal/                # 定点数封装（或用 shopspring/decimal）
└── go.mod
```