async function refreshPrices() {
    const res = await fetch('/api/prices');
    const data = await res.json();
    const table = document.getElementById('priceTable');
    table.innerHTML = '<tr><th>币种</th><th>价格 (USDT)</th></tr>';
    data.forEach(d => {
      const row = `<tr><td>${d.symbol}</td><td>${d.price.toFixed(3)}</td></tr>`;
      table.innerHTML += row;
    });
  }
  
  async function refreshSystem() {
    const res = await fetch('/api/system');
    const data = await res.json();
    document.getElementById('sysinfo').textContent = JSON.stringify(data, null, 2);
  }
  
  async function refreshQuote() {
    const res = await fetch('/api/quotes');
    const data = await res.json();
    document.getElementById('quote').textContent = data.quote;
  }
  
  function openTab(tab) {
    document.querySelectorAll('.tab').forEach(div => div.style.display = 'none');
    document.getElementById(tab).style.display = 'block';
  }
  
  function refreshTime() {
    document.getElementById('time').textContent = "最后更新时间: " + new Date().toLocaleString();
  }
  
  setInterval(() => { refreshPrices(); refreshSystem(); refreshQuote(); refreshTime(); }, 2000);
  refreshPrices(); refreshSystem(); refreshQuote(); refreshTime();
  