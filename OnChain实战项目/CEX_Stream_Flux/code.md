下面是一套可直接开干的最小可用（MVP）代码模板与脚手架。结构聚焦：Go 采集器（Binance/OKX WS + REST 回补）→ Kafka/Redpanda → Flink SQL 聚合 → ClickHouse DDL → Go API → 告警规则 → 配置样例。

---

## 目录结构

```
.
├── collector/
│   ├── cmd/collector/main.go
│   ├── go.mod
│   └── internal/
│       ├── bus/kafka_producer.go
│       ├── exchange/binance_ws.go
│       ├── exchange/okx_ws.go
│       ├── exchange/common.go
│       ├── model/events.proto
│       └── util/time.go
├── backfill/
│   ├── cmd/backfill/main.go
│   └── go.mod
├── api/
│   ├── main.go
│   └── go.mod
├── flink/
│   └── ohlcv_1s.sql
├── ddl/
│   └── clickhouse.sql
├── alert/
│   └── rules.yaml
├── configs/
│   ├── exchanges.yaml
│   └── symbols.yaml
└── infra/
    └── docker-compose.yml
```

---

## collector/go.mod

```go
module ts-monitor/collector

go 1.22

require (
	github.com/confluentinc/confluent-kafka-go/v2 v2.6.0
	github.com/goccy/go-json v0.10.3
	github.com/gorilla/websocket v1.5.1
	google.golang.org/protobuf v1.34.1
)
```

---

## collector/cmd/collector/main.go

```go
package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"

	"ts-monitor/collector/internal/bus"
	"ts-monitor/collector/internal/exchange"
)

func main() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// graceful stop
	go func() {
		ch := make(chan os.Signal, 1)
		signal.Notify(ch, syscall.SIGINT, syscall.SIGTERM)
		<-ch
		cancel()
	}()

	producer, err := bus.NewKafkaProducer(bus.KafkaConfig{
		Brokers: os.Getenv("KAFKA_BROKERS"),
		TopicTrades: "trades.raw",
	})
	if err != nil { log.Fatal(err) }
	defer producer.Close()

	// load configs (省略：可读取 configs/exchanges.yaml)
	syms := []string{"BTCUSDT", "ETHUSDT"}

	bin := exchange.NewBinanceWS(producer)
	okx := exchange.NewOkxWS(producer)

	go bin.Run(ctx, syms)
	go okx.Run(ctx, syms)

	<-ctx.Done()
	log.Println("collector exit")
}
```

---

## collector/internal/exchange/common.go

```go
package exchange

type Trade struct {
	Exchange string  `json:"exchange"`
	Symbol   string  `json:"symbol"`
	TsMs     int64   `json:"tsms"`    // event time
	Price    float64 `json:"price"`
	Size     float64 `json:"size"`
	IsBuy    bool    `json:"is_buy"`
	RecvMs   int64   `json:"recv_ms"`
	TradeID  string  `json:"trade_id"`
}
```

---

## collector/internal/exchange/binance_ws.go

```go
package exchange

import (
	"context"
	"log"
	"net/url"
	"strings"
	"time"

	"github.com/goccy/go-json"
	"github.com/gorilla/websocket"
	"ts-monitor/collector/internal/bus"
	"ts-monitor/collector/internal/util"
)

type BinanceWS struct{ prod *bus.KafkaProducer }

func NewBinanceWS(p *bus.KafkaProducer) *BinanceWS { return &BinanceWS{prod: p} }

func (b *BinanceWS) Run(ctx context.Context, symbols []string) {
	// stream e.g.: wss://stream.binance.com:9443/stream?streams=btcusdt@trade
	streams := make([]string, 0, len(symbols))
	for _, s := range symbols {
		streams = append(streams, strings.ToLower(s)+"@trade")
	}
	u := url.URL{Scheme: "wss", Host: "stream.binance.com:9443", Path: "/stream", RawQuery: "streams=" + strings.Join(streams, "/")}

	retry := 0
	for ctx.Err() == nil {
		c, _, err := websocket.DefaultDialer.Dial(u.String(), nil)
		if err != nil {
			log.Printf("binance dial err: %v", err)
			time.Sleep(time.Second * time.Duration(util.Backoff(retry)))
			retry++
			continue
		}
		retry = 0
		log.Printf("binance connected: %s", u.String())

		c.SetReadLimit(1 << 20)
		c.SetReadDeadline(time.Now().Add(30 * time.Second))
		c.SetPongHandler(func(string) error { c.SetReadDeadline(time.Now().Add(30 * time.Second)); return nil })

		go func() { // ping
			Ticker := time.NewTicker(15 * time.Second)
			defer Ticker.Stop()
			for {
				select { case <-ctx.Done(): return; case <-Ticker.C: _ = c.WriteMessage(websocket.PingMessage, nil) }
			}
		}()

		for ctx.Err() == nil {
			_, msg, err := c.ReadMessage()
			if err != nil { log.Printf("binance read err: %v", err); break }
			// {"stream":"btcusdt@trade","data":{"e":"trade","E":1690000000000,"s":"BTCUSDT","t":1,"p":"30000.1","q":"0.01","m":true}}
			var envelope struct{ Stream string; Data struct{ E int64; S, P, Q string; T int64; M bool; Tt int64 `json:"t"` } }
			if err := json.Unmarshal(msg, &envelope); err != nil { continue }

			px := util.ParseFloat(envelope.Data.P)
			sz := util.ParseFloat(envelope.Data.Q)
			tr := Trade{
				Exchange: "binance",
				Symbol:   envelope.Data.S,
				TsMs:     envelope.Data.E,
				Price:    px,
				Size:     sz,
				IsBuy:    !envelope.Data.M, // maker is seller => taker buy
				RecvMs:   time.Now().UnixMilli(),
				TradeID:  util.Itoa64(envelope.Data.T),
			}
			b.prod.EmitTrade(ctx, tr)
		}
		_ = c.Close()
		time.Sleep(time.Second * time.Duration(util.Backoff(retry)))
		retry++
	}
}
```

---

## collector/internal/exchange/okx_ws.go

```go
package exchange

import (
	"context"
	"log"
	"time"

	"github.com/goccy/go-json"
	"github.com/gorilla/websocket"
	"ts-monitor/collector/internal/bus"
	"ts-monitor/collector/internal/util"
)

type OkxWS struct{ prod *bus.KafkaProducer }

func NewOkxWS(p *bus.KafkaProducer) *OkxWS { return &OkxWS{prod: p} }

func (o *OkxWS) Run(ctx context.Context, symbols []string) {
	// public trades channel
	c, _, err := websocket.DefaultDialer.Dial("wss://ws.okx.com:8443/ws/v5/public", nil)
	if err != nil { log.Printf("okx dial err: %v", err); return }
	defer c.Close()

	subs := struct {
		Op   string `json:"op"`
		Args []map[string]string `json:"args"`
	}{Op: "subscribe"}
	for _, s := range symbols {
		subs.Args = append(subs.Args, map[string]string{"channel":"trades","instId": s[:3]+"-USDT-SWAP"}) // 简化：现货可用 SPOT
	}
	_ = c.WriteJSON(subs)

	c.SetReadLimit(1<<20)
	c.SetReadDeadline(time.Now().Add(30*time.Second))
	c.SetPongHandler(func(string) error { c.SetReadDeadline(time.Now().Add(30*time.Second)); return nil })

	go func(){
		Ticker := time.NewTicker(15*time.Second)
		defer Ticker.Stop()
		for { select{ case <-ctx.Done(): return; case <-Ticker.C: _ = c.WriteMessage(websocket.PingMessage, nil) } }
	}()

	for ctx.Err()==nil {
		_, msg, err := c.ReadMessage()
		if err != nil { log.Printf("okx read err: %v", err); return }
		var env struct{ Arg struct{ InstId string `json:"instId"` }; Data []struct{ Ts string; Px string; Sz string; Side string; TrdId string } }
		if err := json.Unmarshal(msg, &env); err != nil { continue }
		for _, d := range env.Data {
			tr := Trade{
				Exchange: "okx",
				Symbol:   env.Arg.InstId,
				TsMs:     util.ParseInt64(d.Ts),
				Price:    util.ParseFloat(d.Px),
				Size:     util.ParseFloat(d.Sz),
				IsBuy:    d.Side=="buy",
				RecvMs:   time.Now().UnixMilli(),
				TradeID:  d.TrdId,
			}
			o.prod.EmitTrade(ctx, tr)
		}
	}
}
```

---

## collector/internal/bus/kafka_producer.go

```go
package bus

import (
	"context"
	"log"
	"os"

	"github.com/confluentinc/confluent-kafka-go/v2/kafka"
	"github.com/goccy/go-json"
)

type KafkaConfig struct { Brokers string; TopicTrades string }

type KafkaProducer struct { p *kafka.Producer; topicTrades string }

func NewKafkaProducer(cfg KafkaConfig) (*KafkaProducer, error) {
	p, err := kafka.NewProducer(&kafka.ConfigMap{
		"bootstrap.servers": cfg.Brokers,
		"enable.idempotence": true,
		"acks": "all",
	})
	if err != nil { return nil, err }
	kp := &KafkaProducer{p: p, topicTrades: cfg.TopicTrades}
	go func() { for e := range p.Events() { _ = e } }() // drain
	return kp, nil
}

func (k *KafkaProducer) Close() { k.p.Close() }

func (k *KafkaProducer) EmitTrade(ctx context.Context, v any) {
	b, _ := json.Marshal(v)
	err := k.p.Produce(&kafka.Message{
		TopicPartition: kafka.TopicPartition{Topic: &k.topicTrades, Partition: kafka.PartitionAny},
		Value: b,
		Headers: []kafka.Header{{Key:"source", Value:[]byte(os.Getenv("NODE_ID"))}},
	}, nil)
	if err != nil { log.Printf("produce err: %v", err) }
}
```

---

## collector/internal/model/events.proto

```proto
syntax = "proto3";
package events;
option go_package = "ts-monitor/collector/internal/model;model";

message Trade {
  string exchange = 1;
  string symbol   = 2;
  int64  tsms     = 3;
  double price    = 4;
  double size     = 5;
  bool   is_buy   = 6;
  int64  recv_ms  = 7;
  string trade_id = 8;
}
```

---

## collector/internal/util/time.go

```go
package util

import (
	"strconv"
)

func ParseFloat(s string) float64 { v, _ := strconv.ParseFloat(s, 64); return v }
func ParseInt64(s string) int64   { v, _ := strconv.ParseInt(s, 10, 64); return v }
func Itoa64(v int64) string       { return strconv.FormatInt(v, 10) }

func Backoff(retry int) int {
	if retry < 1 { return 1 }
	if retry > 6 { retry = 6 }
	b := 1 << retry // 2^retry
	if b > 32 { b = 32 }
	return b
}
```

---

## backfill/go.mod

```go
module ts-monitor/backfill

go 1.22

require (
	github.com/goccy/go-json v0.10.3
)
```

---

## backfill/cmd/backfill/main.go

```go
package main

import (
	"context"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/goccy/go-json"
)

type Kline struct { OpenTime int64 `json:"0"`; Open string `json:"1"`; High string `json:"2"`; Low string `json:"3"`; Close string `json:"4"`; Volume string `json:"5"` }

func main(){
	// 简化示例：拉取 Binance 1m kline 并打印为 CSV，可改写落地 S3/ClickHouse
	sym := envOr("SYM", "BTCUSDT")
	start := envOr("START", "1690000000000") // ms
	url := fmt.Sprintf("https://api.binance.com/api/v3/klines?symbol=%s&interval=1m&startTime=%s&limit=1000", sym, start)
	resp, err := http.Get(url); if err!=nil { log.Fatal(err) }
	defer resp.Body.Close()
	b, _ := io.ReadAll(resp.Body)
	var arr [][]any
	_ = json.Unmarshal(b, &arr)
	for _, row := range arr {
		fmt.Printf("%v,%v,%v,%v,%v,%v\n", row[0], row[1], row[2], row[3], row[4], row[5])
	}
	_ = time.Second
}

func envOr(k, d string) string { v := os.Getenv(k); if v=="" { return d }; return v }
```

---

## api/go.mod

```go
module ts-monitor/api

go 1.22

require (
	github.com/go-chi/chi/v5 v5.1.0
	github.com/jmoiron/sqlx v1.4.0
	github.com/ClickHouse/clickhouse-go/v2 v2.29.1
)
```

---

## api/main.go

```go
package main

import (
	"database/sql"
	"log"
	"net/http"
	"time"

	ch "github.com/ClickHouse/clickhouse-go/v2"
	"github.com/go-chi/chi/v5"
	"github.com/jmoiron/sqlx"
)

func main(){
	dsn := ch.DSN{ Addr: []string{"localhost:9000"}, Database: "market", Protocol: ch.Native }
	db := sqlx.NewDb(ch.OpenDB(&dsn), "clickhouse")
	defer db.Close()

	r := chi.NewRouter()
	r.Get("/v1/price/{symbol}", func(w http.ResponseWriter, r *http.Request){
		sym := chi.URLParam(r, "symbol")
		var px float64
		err := db.QueryRow("SELECT price FROM trades WHERE symbol=? ORDER BY ts DESC LIMIT 1", sym).Scan(&px)
		if err!=nil { http.Error(w, err.Error(), http.StatusNotFound); return }
		w.Header().Set("Content-Type","application/json")
		w.Write([]byte(fmtJson(map[string]any{"symbol":sym, "price":px})))
	})

	r.Get("/v1/kline/{symbol}", func(w http.ResponseWriter, r *http.Request){
		sym := chi.URLParam(r, "symbol")
		rows, err := db.Queryx(`SELECT bucket, open, high, low, close, vol FROM kline_1s WHERE symbol=? ORDER BY bucket DESC LIMIT 120` , sym)
		if err!=nil { http.Error(w, err.Error(), 500); return }
		defer rows.Close()
		var out []map[string]any
		for rows.Next(){
			var t time.Time; var o,h,l,c float64; var v float64
			if err:= rows.Scan(&t,&o,&h,&l,&c,&v); err==nil {
				out = append(out, map[string]any{"t":t,"o":o,"h":h,"l":l,"c":c,"v":v})
			}
		}
		w.Header().Set("Content-Type","application/json")
		w.Write([]byte(fmtJson(out)))
	})

	log.Println("api on :8080")
	http.ListenAndServe(":8080", r)
}

func fmtJson(v any) string { b, _ := json.Marshal(v); return string(b) }
```

---

## flink/ohlcv_1s.sql

```sql
-- Flink SQL: 从 trades.raw(JSON) 聚合 1s OHLCV，写入 ClickHouse sink（可改为 JDBC/Upsert）
CREATE TABLE trades_raw (
  `exchange` STRING,
  `symbol`   STRING,
  `tsms`     BIGINT,
  `price`    DOUBLE,
  `size`     DOUBLE,
  `is_buy`   BOOLEAN,
  `recv_ms`  BIGINT,
  `trade_id` STRING,
  `ts` AS TO_TIMESTAMP_LTZ(tsms, 3),
  WATERMARK FOR ts AS ts - INTERVAL '3' SECOND
) WITH (
  'connector' = 'kafka',
  'topic' = 'trades.raw',
  'properties.bootstrap.servers' = 'localhost:9092',
  'format' = 'json',
  'scan.startup.mode' = 'latest-offset'
);

CREATE TABLE kline_1s (
  symbol STRING,
  bucket TIMESTAMP(3),
  open   DOUBLE,
  high   DOUBLE,
  low    DOUBLE,
  close  DOUBLE,
  vol    DOUBLE
) WITH (
  'connector'='jdbc',
  'url'='jdbc:clickhouse://localhost:9000/market',
  'table-name'='kline_1s',
  'driver'='com.clickhouse.jdbc.ClickHouseDriver'
);

INSERT INTO kline_1s
SELECT
  symbol,
  TUMBLE_START(ts, INTERVAL '1' SECOND) AS bucket,
  FIRST_VALUE(price) AS open,
  MAX(price) AS high,
  MIN(price) AS low,
  LAST_VALUE(price) AS close,
  SUM(size) AS vol
FROM trades_raw
GROUP BY symbol, TUMBLE(ts, INTERVAL '1' SECOND);
```

---

## ddl/clickhouse.sql

```sql
CREATE DATABASE IF NOT EXISTS market;

USE market;

CREATE TABLE IF NOT EXISTS trades (
  event_date Date DEFAULT toDate(ts),
  ts         DateTime64(3, 'UTC'),
  exchange   LowCardinality(String),
  symbol     LowCardinality(String),
  trade_id   String,
  price      Decimal(20,8),
  size       Decimal(20,8),
  is_buy     UInt8,
  source_lag_ms UInt32
) ENGINE = MergeTree
PARTITION BY toYYYYMM(event_date)
ORDER BY (symbol, ts)
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS kline_1s (
  symbol LowCardinality(String),
  bucket DateTime64(3, 'UTC'),
  open   Float64,
  high   Float64,
  low    Float64,
  close  Float64,
  vol    Float64
) ENGINE = ReplacingMergeTree
PARTITION BY toYYYYMM(bucket)
ORDER BY (symbol, bucket);
```

---

## alert/rules.yaml

```yaml
# 简易告警规则示例（供自研 Alert Engine 解析）
- name: spread_binance_okx_btc
  expr: "abs(price.binance.BTCUSDT - price.okx.BTCUSDT)/price.binance.BTCUSDT > 0.001"
  for: 5s
  severity: P2
  notify: [lark]

- name: ema_cross_sol
  expr: "ema(price.smooth.SOLUSDT, 20) > ema(price.smooth.SOLUSDT, 200)"
  for: 0s
  severity: P3
  notify: [lark]

- name: source_drop_binance
  expr: "rate(collector_in_msgs_total{exchange='binance'}[1m]) < 0.5 * avg_over_time(collector_in_msgs_total{exchange='binance'}[15m])"
  for: 1m
  severity: P1
  notify: [lark, email]
```

---

## configs/exchanges.yaml

```yaml
binance:
  ws: wss://stream.binance.com:9443/stream
  rest: https://api.binance.com
  snapshot_interval: 300s
  reconnect_backoff: [1s, 32s]

okx:
  ws: wss://ws.okx.com:8443/ws/v5/public
  rest: https://www.okx.com
  reconnect_backoff: [1s, 32s]
```

---

## configs/symbols.yaml

```yaml
symbols:
  - BTCUSDT
  - ETHUSDT
  - SOLUSDT
precision:
  BTCUSDT: { price: 2, size: 6 }
  ETHUSDT: { price: 2, size: 6 }
  SOLUSDT: { price: 3, size: 2 }
```

---

## infra/docker-compose.yml

```yaml
version: "3.9"
services:
  redpanda:
    image: redpandadata/redpanda:v24.1.10
    command: ["redpanda","start","--overprovisioned","--smp","1","--memory","1G","--reserve-memory","0M","--node-id","0","--check=false"]
    ports: ["9092:9092"]

  clickhouse:
    image: clickhouse/clickhouse-server:24.8
    ports: ["9000:9000","8123:8123"]
    ulimits:
      nofile: { soft: 262144, hard: 262144 }

  grafana:
    image: grafana/grafana:11.1.0
    ports: ["3000:3000"]
```

---

### 运行提示

1. `docker compose -f infra/docker-compose.yml up -d`
2. 在 ClickHouse 执行 `ddl/clickhouse.sql`
3. 启动 collector：

```
cd collector && KAFKA_BROKERS=localhost:9092 go run ./cmd/collector
```

4. 跑 Flink SQL（或先用 API 写入 trades/kline_1s 调试）
5. 启动 API：

```
cd api && go run .
```

> 以上模板偏简化，生产需要补充：重试/幂等键、WS 限流与速率控制、统一 symbol 映射、指标埋点、配置热更新、REST 回补与对账、物化视图/流式写 ClickHouse、更完备的告警引擎等。




已把一整套可跑的「代码模板脚手架」放到右侧画布里了（含 Go 采集器、Kafka/Redpanda、Flink SQL、ClickHouse DDL、Go API、告警规则、配置与 docker-compose）。

- todo
* Binance/OKX 采集器 + 本地 Redpanda 单节点压测脚本
* Flink 到 ClickHouse 的 JDBC sink 可执行示例
* API 查询端加上 Redis 缓存与限流