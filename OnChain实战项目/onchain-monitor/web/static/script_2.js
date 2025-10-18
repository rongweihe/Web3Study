// web/static/script.js
// 责任：
// - 拉取 /api/prices (2s)，/api/system (5s)，/api/quotes (5s)，/api/eth_top5 (10s)
// - 渲染到 index.html 中对应的 DOM（id 匹配）
// - 兼容后端返回的几种常见格式

function safeNum(v){
    if (typeof v === 'number') return v;
    if (!v) return 0;
    const n = parseFloat(String(v).replace(/,/g,''));
    return isNaN(n)?0:n;
  }
  function fmtTime(t){
    try {
      const d = new Date(t);
      if (isNaN(d)) return String(t);
      return d.toLocaleString();
    } catch(e){ return String(t); }
  }
  async function fetchJSON(url){
    try {
      const res = await fetch(url, {cache:"no-store"});
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return await res.json();
    } catch(e){
      console.warn('fetch error', url, e);
      return null;
    }
  }
  
  /* ---------- Prices ---------- */
  /*
   Expected backend shapes:
   1) [{"symbol":"BTC","price":123},{"symbol":"ETH","price":...}, ...]
   2) {"BTC": {"price":123,...}, "ETH":{...}, ...}
   3) {"data":[...], "lastUpdate":...}
   This function normalizes to array of {symbol, price}
  */
  function normalizePrices(raw){
    if (!raw) return [];
    if (Array.isArray(raw)){
      return raw.map(it=>{
        return { symbol: it.symbol || it.Symbol || it.sym || '', price: safeNum(it.price || it.last || it.close || it.value) }
      });
    }
    // wrapper
    if (raw.data && Array.isArray(raw.data)){
      return normalizePrices(raw.data);
    }
    // object keyed by symbol
    if (typeof raw === 'object'){
      const out = [];
      for (const k of Object.keys(raw)){
        const v = raw[k];
        if (v && typeof v === 'object'){
          out.push({symbol:k, price: safeNum(v.price || v.last || v.close || v.value)});
        } else {
          out.push({symbol:k, price: safeNum(v)});
        }
      }
      return out;
    }
    return [];
  }
  
  function renderPrices(list){
    const el = document.getElementById('price-content');
    if (!list || list.length===0){
      el.innerHTML = '<div class="placeholder">无价格数据</div>'; return;
    }
    const container = document.createElement('div');
    container.className = 'price-list';
    list.forEach(it=>{
      const row = document.createElement('div');
      row.className = 'price-item';
      row.innerHTML = `<div class="price-symbol">${it.symbol}</div><div>${Number(it.price).toLocaleString(undefined,{maximumFractionDigits:8})}</div>`;
      container.appendChild(row);
    });
    el.innerHTML = '';
    el.appendChild(container);
  }
  
  /* ---------- System ---------- */
  function renderSystem(raw){
    const el = document.getElementById('system-content');
    if (!raw){ el.innerHTML = '<div class="placeholder">无系统数据</div>'; return; }
    // 尝试常见字段
    const cpu = raw.cpu_percent || raw.cpuPercent || raw.cpu || raw.cpu_usage || raw.cpuPercentile;
    const mem = raw.mem_used || raw.memMB || raw.mem || raw.memory || raw.mem_used_mb;
    const gor = raw.num_goroutine || raw.goNum || raw.goroutines || raw.go_num;
    // 构造显示
    const lines = [];
    lines.push(`<div>CPU: ${cpu !== undefined ? cpu : (raw.cpu || 'N/A')}</div>`);
    let memText = 'N/A';
    if (typeof mem === 'number') memText = (mem/1024/1024).toFixed(2) + ' MB';
    else if (typeof mem === 'string') memText = mem;
    else if (raw.memMB) memText = raw.memMB;
    lines.push(`<div>内存: ${memText}</div>`);
    lines.push(`<div>Goroutine: ${gor !== undefined ? gor : (raw.goNum || 'N/A')}</div>`);
    lines.push(`<div class="placeholder">raw: ${JSON.stringify(raw).slice(0,120)}${JSON.stringify(raw).length>120?'...':''}</div>`);
    el.innerHTML = lines.join('');
  }
  
  /* ---------- Quote ---------- */
  function renderQuote(q){
    const el = document.getElementById('quote-content');
    if (!q){ el.innerText = '无金句'; return; }
    // q may be {quote:"..."} or string
    if (typeof q === 'string') el.innerText = q;
    else el.innerText = q.quote || q.text || JSON.stringify(q);
  }
  
  /* ---------- ETH Top5 ---------- */
  function renderEthTop(list){
    const tbody = document.getElementById('transfer-body');
    if (!list || list.length===0){
      tbody.innerHTML = '<tr><td colspan="3" class="placeholder">暂无大额转账记录</td></tr>'; return;
    }
    tbody.innerHTML = list.map(it=>{
      const addr = it.address || it.to || it.toAddress || it.addr || it.From || '';
      const amt = safeNum(it.amount || it.Value || it.value || it.amountEth || 0);
      const time = it.time || it.timestamp || it.timeStr || '';
      return `<tr><td>${addr}</td><td>${amt.toFixed(2)}</td><td>${fmtTime(time)}</td></tr>`;
    }).join('');
  }
  
  /* ---------- Polling schedule ---------- */
  async function updatePrices(){
    const raw = await fetchJSON('/api/prices');
    const list = normalizePrices(raw);
    renderPrices(list);
  }
  async function updateSystem(){
    const raw = await fetchJSON('/api/system');
    renderSystem(raw);
  }
  async function updateQuote(){
    const raw = await fetchJSON('/api/quotes');
    renderQuote(raw);
  }
  async function updateEthTop(){
    const raw = await fetchJSON('/api/eth_top5');
    // accept either array or {result: array}
    const list = Array.isArray(raw) ? raw : (raw && Array.isArray(raw.result) ? raw.result : []);
    renderEthTop(list);
    return;
  }
  
  async function tickAll(){
    // prices every 2s, quotes/system every 5s, eth top5 every 10s
    updatePrices();
    // update others according to their own timers by setInterval below
  }
  
  // initial
  tickAll();
  updateSystem(); updateQuote(); updateEthTop();
  
  // timers
  setInterval(updatePrices, 2000);   // 2s price
  setInterval(updateSystem, 5000);   // 5s system
  setInterval(updateQuote, 5000);    // 5s quote
  setInterval(updateEthTop, 10000);  // 10s eth top
  
  // update footer time
  setInterval(()=> {
    const el = document.getElementById('last-update');
    el.innerText = '最后更新时间: ' + new Date().toLocaleString();
  }, 2000);
  