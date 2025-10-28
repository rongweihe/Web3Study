# 基于交易数据的时序数据监控采集分析平台

一套“能快速落地、后续可演进到高并发高可靠”的技术调研要点 + 目标架构 + 核心模块设计，默认数据源覆盖 CEX（Binance/OKX/Bybit…）与 DEX（Uniswap/Pancake/链上节点），语言以 Go 为主、Python 做数据与离线分析。

---

# 一、技术调研清单（做或不做的判断标准）

**1) 数据源与协议**

* CEX：WebSocket（深度、成交、标记价、指数价、资金费率）、REST（k线、历史、账户持仓*若仅行情则忽略*）。

  * 关键：消息频率上限/限流、心跳与重连策略、快照+增量深度一致性、时间戳语义（成交时间 vs 服务器生成时间）。
* DEX/链上：节点/第三方 RPC、事件日志（Swap/Sync）、The Graph / Subgraph（延迟与回溯能力）、MEV/区块重组应对。

  * 关键：块时间抖动、reorg 容忍、交易确认策略（N 个确认再落库 vs 先软写入）。
* 指标/参考价：Chainlink/自研指数。关注取样频率、滑点、熔断条件。

**2) 数据建模与存储**

* 热数据（< 7 天）：ClickHouse 或 TimescaleDB（高压缩+高并发查询）。
* 温/冷数据：S3/OSS + Parquet（周/月分区），DuckDB/Presto 做快速 ad-hoc。
* KV/缓存：Redis（实时窗口、去重、平滑状态 PriceSmooth、最新快照）。
* 评估：ClickHouse 的 MergeTree vs Replacing/Summing/Collapsing；TTLs；低基数字段（交易对、交易所）作为分区/索引。

**3) 流处理与总线**

* Kafka/Redpanda（主干总线）：exactly-once 语义成本 vs 至少一次 + 去重策略。
* 流处理：Flink（SQL/CEP）或 Kafka Streams（Go 可选：Materialize/ksqldb）
* 回放与回补：Kafka topics + 时间段重放 / S3 历史回灌。

**4) 计算与指标**

* 实时：OHLCV 聚合（1s/5s/1m…）、VWAP、盘口不平衡、资金费率监控、跨市价差、指数/标记价偏离（oracle divergence）。
* 批处理：T+1 回溯校验、数据质量审计（丢包率、乱序率、时钟漂移）。

**5) 可观测与治理**

* Prometheus/Grafana：延迟 P95、每源 QPS、丢包/重连次数、乱序比例、回溯修正量。
* 数据质量（DQ）：schema 校验（Protobuf/Avro）、时间戳单调性、逻辑约束（价格>0、深度合规）。
* 容灾：多机房/多 Region、跨供应商 RPC、断点续传 offset 管理。

---

# 二、目标架构（自小到大演进路径）

```
[CEX/DEX/RPC]  ->  [Collector(Go)]  ->  [Normalizer]  ->  [Kafka/Redpanda]
                                                       |-> [Flink SQL/CEP: 实时聚合、校验、告警]
                                                       |-> [OHLCV Builder]
                                   [Redis(快照/平滑状态)] |
[Backfill Service]  <->  [S3 Parquet 历史层] <----------/
                         |                             \
                         -> [Batch(Glue/Spark/DuckDB)]  -> [ClickHouse 热库]
                                                          \
                                                           -> [API/Query Service(Go)]
                                                           -> [Alert Engine(Go/Py)]
                                                           -> [Grafana/Noti(Lark/Slack/Email)]
```

**MVP（两周内可跑）**
Go Collector（Binance/OKX WS + REST backfill）→ 内部 NATS/Kafka → ClickHouse（行情 & k线）→ 简易 Grafana 大盘（价差/偏离/延迟）→ Lark 告警。
**升级**
加入链上 DEX、Flink SQL 聚合、S3/Parquet 冷存、回放回灌、CEP 异常检测、跨所指数与 PriceSmooth（你已有经验）制度化。

---

# 三、核心模块设计

## 1) Collector（多源采集器）

职责：稳定连入、限流、心跳与自动重连、断线重放、快照+增量合并、严格时间戳。

* **关键点**

  * WS + REST“双通道”：WS 实时增量，定时 REST 校验对齐（如每 5 分钟拉快照对比校正）。
  * 去重：以 `(exchange, symbol, event_type, sequence_id|ts)` 做幂等。
  * 时钟：统一使用源时间戳（若有）+ 本地接收时间；记录 `source_lag_ms`。

* **消息模型 (Protobuf 建议)**

  ```proto
  message Trade {
    string exchange = 1;    // "binance"
    string symbol   = 2;    // "BTCUSDT"
    int64  tsms     = 3;    // event time (ms)
    string trade_id = 4;
    double price    = 5;
    double size     = 6;
    bool   is_buy   = 7;    // taker side
    int64  recv_ms  = 8;    // local receive time
  }

  message OrderBookDelta {
    string exchange = 1;
    string symbol   = 2;
    int64  tsms     = 3;
    uint64 seq      = 4;
    repeated PriceLevel bids = 5;
    repeated PriceLevel asks = 6;
  }

  message PriceLevel { double px = 1; double qty = 2; }
  ```

* **重连与一致性**

  * 深度：`GetSnapshot(seq_s) -> apply deltas where seq>seq_s`；校正失败自动重建。

## 2) Normalizer（标准化与校验）

* 统一 symbol（`BTCUSDT`⇄`BTC-USD-SWAP`），资产精度、小数位，时间戳落到 UTC 毫秒。
* 规则引擎：价格<=0、数量<=0 直接丢弃并计数；极端跳变进入“隔离队列”。

## 3) Event Bus（Kafka/Redpanda）

* 主题划分：`trades.raw`, `depth.delta`, `reference.prices`, `trades.norm`, `kline.1s/1m`, `alerts`.
* 分区键：`symbol` 或 `symbol%N` 保序；压缩 zstd；开启 idempotent producer。
* 存储保留：热 7 天；旁路 sink 到 S3（Kafka Connect/Spark sink）。

## 4) 实时计算（Flink SQL/CEP）

* 典型作业：

  * **OHLCV**：1s/5s/1m tumbling windows；支持延迟水位（watermark 2–5s）与迟到数据合并。
  * **VWAP / 盘口不平衡 (OBI)**：滚动窗口（10s/1m）。
  * **偏离检测**：`|index - mark| / index > X%` 持续 T 秒 → 告警。
  * **平滑价格 PriceSmooth**：将你已有 60s 最大过渡的状态机放到 Flink keyed state；输出 `price.smooth`.

## 5) 存储层

### ClickHouse 热库（建议）

* **表：原始成交**

  ```sql
  CREATE TABLE trades (
    event_date Date DEFAULT toDate(ts),
    ts         DateTime64(3, 'UTC'),
    exchange   LowCardinality(String),
    symbol     LowCardinality(String),
    trade_id   String,
    price      Decimal(18,8),
    size       Decimal(18,8),
    is_buy     UInt8,
    source_lag_ms UInt32
  )
  ENGINE = MergeTree
  PARTITION BY toYYYYMM(event_date)
  ORDER BY (symbol, ts);
  ```
* **表：k线（1s/1m）**：使用 `AggregatingMergeTree` 或直接物化视图从 trades 汇聚。
* **表：指标与告警**：`alerts`（时间、维度、阈值、上下文快照）。

### 冷存：S3/Parquet

* 分区：`dt=YYYY-MM-DD/exchange=symbol=...`
* 每小时/每天滚动落盘，元数据写入 Hive Metastore 或 Glue Catalog，便于 Presto/DuckDB 查询。

### Redis

* `symbol:last_trade`、`symbol:orderbook_snapshot`、`symbol:price_smooth_state`
* TTL 控制 + 持久化 AOF（可选）以便服务重启快速恢复。

## 6) API / Query Service（Go）

* 查询：最新价/盘口、区间 k 线、因子（OBI/VWAP）、跨所价差。
* 特性：多维聚合（symbol/exchange/timeframe）、多租户限流、缓存（Redis/内存）。
* GraphQL 或 REST；对外 SLA（p95<100ms 针对热查询）。

## 7) Alert Engine（Go/Python）

* 规则类型：

  * 阈值类：`spread(Binance,OKX,BTCUSDT) > 10 bps` 持续 5s。
  * 形态类：`EMA20 上穿 EMA200`（你已有）+ 波动熔断。
  * 数据质量：某源 1 分钟内丢包率>1%、乱序率>2%、重连>3 次。
* 通道：Lark/Slack/Email；分级（P1/P2）、合并（告警风暴抑制），支持静默策略。

## 8) Backfill & Replay（历史回灌）

* Backfill Service：

  * CEX REST 拉历史 k 线/成交，落地 S3→ClickHouse。
  * DEX 走链上日志区块范围拉取；reorg 安全区（例如确认 12 块后写“定版层”）。
* Replay：

  * 指定时间窗从 Kafka/S3 重放到某下游 topic 或重建指标表。

## 9) 数据质量与治理（DQ）

* Schema Registry（Avro/Protobuf）；版本演进与兼容测试。
* 规则样例：

  * `price Δ / dt > X` 触发“极值隔离”；
  * `symbol 活跃度`（每分钟消息数）与七日均值对比跌出 3σ 告警。
* 审计报表：丢包率、延迟直方图、回补覆盖率。

## 10) 可观测性与 SLO

* **SLO**

  * 端到端延迟 P95 ≤ 2s（WS 源→指标可查询）。
  * 缺失率（分钟级 OHLCV 有效分钟数）≥ 99.9%。
  * 重连恢复时间 P95 ≤ 3s。
* **指标**

  * `collector_in_msgs_total{exchange,symbol}`
  * `ws_reconnects_total{exchange}`
  * `event_end2end_latency_ms_histogram`
  * `dq_drop_counter{reason}`
* **Tracing**

  * OpenTelemetry：从 Collector → Normalizer → Flink → API 的 trace id 贯通。

---

# 四、关键工程细节（容易踩坑）

* **顺序与幂等**：至少一次投递 + 去重键（`trade_id`/`seq+ts`）+ ClickHouse ReplacingMergeTree（最后写胜出）可简化实现。
* **水位与迟到**：WS/链上天然乱序，Flink watermark 不要过窄；迟到数据采用补写+物化视图异步修正。
* **跨源对齐**：指数/标记价来自不同源，必须带 `source_ts` 与 `ingest_ts`，比较偏差用 `source_ts`。
* **DEX 链上**：处理 reorg：状态机（pending→confirmed）；“定版层”单独表，API 默认读定版，实时场景可读混合层。
* **指数/平滑**：将 PriceSmooth 状态持久化 Redis，重启后恢复；状态升级要有版本与灰度。

---

# 五、示例：OHLCV 实时物化视图（ClickHouse）

```sql
CREATE MATERIALIZED VIEW mv_trades_to_1s
ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMMDD(ts)
ORDER BY (symbol, toStartOfSecond(ts))
AS
SELECT
  symbol,
  toStartOfSecond(ts) AS bucket,
  anyLast(price)                AS close,
  argMin(price, ts)             AS open,   -- 如需严格开盘价，可在 Flink 端计算后写入
  max(price)                    AS high,
  min(price)                    AS low,
  sumState(size)                AS vol
FROM trades
GROUP BY symbol, bucket;
```

> 实战里更稳的是在 Flink 端做窗口聚合后落地，避免迟到数据频繁“重算”。

---

# 六、配置与部署建议

* **部署**：K8s（Collector 水平扩展、亲和性按 exchange/symbol 分片），Kafka/Redpanda 3–5 节点，ClickHouse 3 副本，Redis 主从+哨兵。
* **配置管理**：`exchanges.yaml`（订阅清单、限流、断线重连间隔、快照周期），`symbols.yaml`（精度、别名）。
* **灰度**：新源/新规则先旁路影子计算，指标对比 1–2 周再切主。
* **成本控制**：冷热分层 + TTL；API 缓存（1s/5s）覆盖 80% 查询。

---

# 七、从 0-1 的一周落地清单（贴合你现状）

**Day1-2**：Go Collector（Binance/OKX 成交+标记价）+ 标准化 → Kafka；Redis 放最新价。
**Day3**：Flink SQL 做 1s/1m OHLCV；ClickHouse 热库与物化视图。
**Day4**：API（最新价/1m k 线/指数偏离）+ Grafana 看板。
**Day5**：Alert（价差、偏离、断流）接 Lark；加上 PriceSmooth 状态机。
**Day6**：S3/Parquet 冷落地 + 简易回放；数据质量指标。
**Day7**：写 SLO & Runbook（断流、重放、回补流程），压测与基准报表。

---
 

* Go Collector 雏形（Binance/OKX WS + REST 回补）
* Flink SQL 的 OHLCV 作业示例
* ClickHouse DDL 全套（trades/kline/alerts）
* Alert 规则样例（EMA20/EMA200、跨所价差、oracle 偏移）
* `exchanges.yaml` 与 `symbols.yaml` 模板
 