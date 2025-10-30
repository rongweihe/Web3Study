// internal/engine/matcher.go
type Matcher struct {
	symbol     string
	ob         *book.OrderBook
	seq        uint64
	ctrl       *Controller
	prod       KafkaProducer[types.OrderEvent]
	repo       Repo          // async MySQL writer
	snap       SnapshotStore // Redis
	lastOffset int64
}

func (m *Matcher) Run(ctx context.Context, cmds <-chan KafkaMsg[types.OrderCommand]) error {
	ticker := time.NewTicker(2 * time.Second) // 快照周期
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case msg := <-cmds:
			if !m.ctrl.IsSymbolOn(m.symbol) {
				// 暂停状态：只 ACK REJECT or 缓存？MVP：直接 Reject 或 Buffer。
				m.emitReject(msg.Value, "SYMBOL_OFF")
				continue
			}
			m.handleCmd(msg)
			m.lastOffset = msg.Offset
		case <-ticker.C:
			m.snapshot()
		}
	}
}

func (m *Matcher) handleCmd(msg KafkaMsg[types.OrderCommand]) {
	c := msg.Value
	switch c.Type {
	case types.CmdNew:
		o := toOrder(c.Order)
		acks, fills := m.ob.Add(o)
		for _, e := range append(acks, fills...) {
			m.emit(e)
		}
	case types.CmdCancel:
		evt, ok := m.ob.Cancel(c.Cancel.OrderID)
		if ok {
			m.emit(evt)
		} else {
			m.emitReject(c, "NOT_FOUND")
		}
	}
}

func (m *Matcher) emit(e types.OrderEvent) {
	m.seq++
	e.Seq = m.seq
	e.Symbol = m.symbol
	e.Ts = time.Now().UnixNano()
	m.prod.Send(e)       // 同步/异步均可，注意 backpressure
	m.repo.AsyncApply(e) // 异步落 MySQL（批量）
}
