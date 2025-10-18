// 文件路径: static/script.js

async function fetchData() {
    try {
        // 1️⃣ 获取币价
        const priceRes = await fetch("/api/prices");
        const prices = await priceRes.json();

        const priceTable = document.querySelector("#price-table tbody");
        priceTable.innerHTML = "";
        prices.forEach(item => {
            const row = `<tr><td>${item.symbol}</td><td>${parseFloat(item.price).toFixed(2)}</td></tr>`;
            priceTable.insertAdjacentHTML("beforeend", row);
        });

        // 2️⃣ 系统状态
        const sysRes = await fetch("/api/system");
        const system = await sysRes.json();
        const sysTable = document.querySelector("#system-table tbody");
        sysTable.innerHTML = `
            <tr><td>CPU 使用率</td><td>${system.cpu}%</td></tr>
            <tr><td>内存使用</td><td>${system.memMB} MB</td></tr>
            <tr><td>Goroutine</td><td>${system.goNum}</td></tr>
        `;

        // 3️⃣ 投资金句
        const quoteRes = await fetch("/api/quotes");
        const quote = await quoteRes.text();
        document.getElementById("quote-content").innerText = quote.quote || quote;

        // 4️⃣ ETH大额转账 Top5
        const txRes = await fetch("/api/eth_top5");
        const txList = await txRes.json();
        const txTable = document.querySelector("#tx-table tbody");
        txTable.innerHTML = "";
        txList.forEach(tx => {
            const row = `<tr><td>${tx.from}</td><td>${tx.to}</td><td>${tx.amount}</td></tr>`;
            txTable.insertAdjacentHTML("beforeend", row);
        });

        // 更新时间
        document.getElementById("last_update").innerText = "最后更新时间: " + new Date().toLocaleString();
    } catch (err) {
        console.error("前端数据加载错误:", err);
    }
}

setInterval(fetchData, 10000);
window.onload = fetchData;
