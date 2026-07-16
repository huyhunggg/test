import os
import json
import zipfile
from pathlib import Path

PROJECT = "vn-stock-radar"

files = {}

files["package.json"] = r'''{
  "name": "vn-stock-radar",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "scan": "node scripts/scan.js"
  },
  "dependencies": {
    "axios": "^1.7.9",
    "technicalindicators": "^3.1.0"
  }
}
'''

files["data.json"] = r'''{
  "updatedAt": "2026-01-01T00:00:00.000Z",
  "count": 2,
  "data": [
    {
      "symbol": "VIC",
      "name": "Tập đoàn Vingroup",
      "industry": "Bất động sản / Holding",
      "price": 216.9,
      "volume": 772500,
      "rsi": 51.24,
      "macd": 2.71,
      "macdSignal": 3.6,
      "macdHistogram": -0.89,
      "ma20": 220.62,
      "ma50": 214.26,
      "ma100": 188.94,
      "change5": 1.2,
      "change20": 8.5,
      "change60": 35.4,
      "volumeRatio20": 1.8,
      "volumeRatio50": 1.4,
      "rs20": 7.2,
      "rs60": 20.5,
      "score": 88,
      "action": "CHỜ ĐIỂM MUA",
      "setup": "Bước nhảy tiềm năng",
      "marketState": "Uptrend mạnh",
      "scoreParts": {
        "trend": 18,
        "momentum": 12,
        "money": 16,
        "setup": 14,
        "vicLeap": 12,
        "risk": 9,
        "relativeStrength": 5
      },
      "categories": [
        "Top cơ hội",
        "Bước nhảy VIC",
        "Dòng tiền mạnh",
        "Tích lũy nền",
        "Tất cả mã"
      ],
      "positives": [
        "Có nhiều đặc điểm tương đồng pha bước nhảy của VIC: tích lũy, dòng tiền, động lượng và sức mạnh tương đối cải thiện.",
        "Giá duy trì trên MA50 và MA100, cấu trúc trung hạn tích cực.",
        "Volume tăng so với trung bình, cho thấy dòng tiền đang chú ý.",
        "Sức mạnh tương đối tốt hơn VNINDEX."
      ],
      "risks": [
        "Giá đang tiệm cận vùng biến động mạnh, nên ưu tiên giải ngân từng phần.",
        "Cần theo dõi phản ứng quanh MA20 và vùng breakout gần nhất."
      ]
    },
    {
      "symbol": "HCM",
      "name": "Chứng khoán HSC",
      "industry": "Chứng khoán",
      "price": 29600,
      "volume": 1500000,
      "rsi": 69.72,
      "macd": 1.23,
      "macdSignal": 0.98,
      "macdHistogram": 0.25,
      "ma20": 28500,
      "ma50": 27000,
      "ma100": 25000,
      "change5": 3.2,
      "change20": 10.24,
      "change60": 22.1,
      "volumeRatio20": 1.4,
      "volumeRatio50": 1.2,
      "rs20": 5.5,
      "rs60": 12.1,
      "score": 86,
      "action": "MUA TỪNG PHẦN",
      "setup": "Breakout 20 phiên",
      "marketState": "Uptrend mạnh",
      "scoreParts": {
        "trend": 20,
        "momentum": 11,
        "money": 18,
        "setup": 14,
        "vicLeap": 8,
        "risk": 10,
        "relativeStrength": 5
      },
      "categories": [
        "Top cơ hội",
        "Breakout 20 phiên",
        "Dòng tiền mạnh",
        "An toàn",
        "Tất cả mã"
      ],
      "positives": [
        "Giá nằm trên MA20, MA50 và MA100.",
        "Xu hướng tăng đang được xác nhận.",
        "Dòng tiền cải thiện so với trung bình."
      ],
      "risks": [
        "RSI tương đối cao, tránh mua đuổi tỷ trọng lớn."
      ]
    }
  ]
}
'''

files["index.html"] = r'''<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8" />
  <title>VN Stock Radar</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />

  <style>
    :root {
      --bg: #f3f6fa;
      --card: #ffffff;
      --text: #0f172a;
      --muted: #64748b;
      --border: #e5e7eb;
      --primary: #071124;
      --green: #16a34a;
      --green-bg: #ecfdf5;
      --orange-bg: #fff7ed;
      --blue-bg: #f5faff;
      --shadow: 0 14px 34px rgba(15, 23, 42, 0.08);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
    }

    .app { padding: 24px; }

    .header {
      background: rgba(255, 255, 255, 0.96);
      border-radius: 28px;
      padding: 18px;
      box-shadow: var(--shadow);
      position: sticky;
      top: 16px;
      z-index: 10;
      backdrop-filter: blur(12px);
    }

    .top {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: center;
      margin-bottom: 16px;
    }

    h1 {
      margin: 0;
      font-size: 24px;
      letter-spacing: -0.04em;
    }

    .subtitle {
      color: var(--muted);
      font-size: 13px;
      margin-top: 5px;
    }

    .live {
      display: flex;
      align-items: center;
      gap: 10px;
      color: var(--muted);
      font-size: 13px;
      white-space: nowrap;
    }

    .dot {
      width: 9px;
      height: 9px;
      background: var(--green);
      border-radius: 999px;
      box-shadow: 0 0 0 5px rgba(22, 163, 74, 0.12);
    }

    .tabs {
      display: flex;
      gap: 10px;
      overflow-x: auto;
      padding-bottom: 12px;
    }

    .tab {
      border: 1px solid var(--border);
      background: white;
      border-radius: 999px;
      padding: 12px 18px;
      font-weight: 800;
      cursor: pointer;
      white-space: nowrap;
      color: #334155;
    }

    .tab.active {
      background: var(--primary);
      color: white;
      border-color: var(--primary);
    }

    .filters {
      display: grid;
      grid-template-columns: 2fr 1fr 1fr 1fr 1fr;
      gap: 12px;
    }

    input, select {
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 15px;
      font-size: 15px;
      width: 100%;
      outline: none;
      background: white;
    }

    .layout {
      display: grid;
      grid-template-columns: minmax(0, 1.45fr) minmax(360px, 0.85fr);
      gap: 24px;
      margin-top: 24px;
    }

    .cards {
      display: grid;
      grid-template-columns: repeat(2, minmax(280px, 1fr));
      gap: 20px;
    }

    .card {
      background: var(--card);
      border-radius: 26px;
      padding: 24px;
      box-shadow: var(--shadow);
      cursor: pointer;
      border: 1px solid transparent;
      transition: 0.18s;
      min-height: 410px;
    }

    .card:hover {
      transform: translateY(-3px);
      border-color: #cbd5e1;
    }

    .card.active {
      border-color: #0f172a;
      box-shadow: 0 18px 44px rgba(15, 23, 42, 0.14);
    }

    .head {
      display: flex;
      justify-content: space-between;
      gap: 16px;
    }

    .symbol {
      font-size: 44px;
      margin: 0;
      letter-spacing: -0.08em;
      font-weight: 950;
      line-height: 1;
    }

    .company {
      color: var(--muted);
      margin-top: 9px;
      line-height: 1.4;
    }

    .badge {
      background: #dcffe8;
      color: #047857;
      padding: 9px 14px;
      border-radius: 999px;
      font-weight: 900;
      height: fit-content;
      white-space: nowrap;
      margin-bottom: 8px;
      text-align: center;
    }

    .badge.vic {
      background: #e0f2fe;
      color: #0369a1;
    }

    .bar {
      height: 9px;
      background: #edf2f7;
      border-radius: 999px;
      overflow: hidden;
      margin: 18px 0;
    }

    .bar span {
      display: block;
      height: 100%;
      background: var(--primary);
    }

    .action {
      font-weight: 950;
      font-size: 20px;
      margin-bottom: 12px;
      letter-spacing: -0.02em;
    }

    .desc {
      color: #475569;
      line-height: 1.55;
      margin-bottom: 16px;
      font-size: 15px;
    }

    .metrics, .scores {
      display: grid;
      gap: 10px;
    }

    .metrics {
      grid-template-columns: repeat(4, 1fr);
      margin-bottom: 10px;
    }

    .scores {
      grid-template-columns: repeat(3, 1fr);
    }

    .box {
      background: var(--blue-bg);
      padding: 12px;
      border-radius: 16px;
      min-height: 62px;
    }

    .label {
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 6px;
    }

    .value {
      font-weight: 900;
      font-size: 15px;
    }

    .tags {
      margin-top: 16px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .tag {
      background: #f8fafc;
      border: 1px solid #edf2f7;
      padding: 7px 11px;
      border-radius: 999px;
      color: #475569;
      font-size: 13px;
    }

    .tag.hot {
      background: #ecfdf5;
      color: #166534;
    }

    .detail {
      background: white;
      border-radius: 28px;
      padding: 28px;
      box-shadow: var(--shadow);
      position: sticky;
      top: 180px;
      max-height: calc(100vh - 200px);
      overflow: auto;
    }

    .detail-symbol {
      font-size: 56px;
      font-weight: 950;
      letter-spacing: -0.08em;
      margin: 0;
      line-height: 1;
    }

    .section {
      border-top: 1px solid var(--border);
      margin-top: 20px;
      padding-top: 20px;
    }

    .section h3 { margin: 0 0 14px; }

    .good, .risk, .neutral {
      border-radius: 16px;
      padding: 14px;
      margin-bottom: 10px;
      line-height: 1.45;
    }

    .good {
      background: var(--green-bg);
      color: #166534;
    }

    .risk {
      background: var(--orange-bg);
      color: #9a3412;
    }

    .neutral {
      background: #f8fafc;
      color: #334155;
    }

    .empty {
      background: white;
      border-radius: 24px;
      box-shadow: var(--shadow);
      padding: 40px;
      color: var(--muted);
      grid-column: 1 / -1;
      text-align: center;
    }

    .footer {
      color: var(--muted);
      font-size: 12px;
      margin-top: 20px;
      line-height: 1.5;
    }

    @media (max-width: 1150px) {
      .layout { grid-template-columns: 1fr; }
      .detail { position: static; max-height: none; }
    }

    @media (max-width: 760px) {
      .app { padding: 12px; }
      .filters { grid-template-columns: 1fr; }
      .cards { grid-template-columns: 1fr; }
      .metrics { grid-template-columns: repeat(2, 1fr); }
      .symbol { font-size: 38px; }
      .detail-symbol { font-size: 46px; }
    }
  </style>
</head>

<body>
  <main class="app">
    <section class="header">
      <div class="top">
        <div>
          <h1>VN Stock Radar</h1>
          <div class="subtitle">
            Quét mã tiềm năng theo Breakout, Pullback, Dòng tiền, MACD, RSI và mẫu “Bước nhảy VIC”
          </div>
        </div>

        <div class="live">
          <span class="dot"></span>
          <span id="updatedAt">Đang tải...</span>
        </div>
      </div>

      <div class="tabs" id="tabs"></div>

      <div class="filters">
        <input id="search" placeholder="Tìm mã, tên công ty, ngành..." />

        <select id="industry">
          <option value="all">Tất cả ngành</option>
        </select>

        <select id="action">
          <option value="all">Tất cả hành động</option>
          <option value="MUA TỪNG PHẦN">Mua từng phần</option>
          <option value="CHỜ ĐIỂM MUA">Chờ điểm mua</option>
          <option value="THEO DÕI">Theo dõi</option>
          <option value="TRÁNH MUA ĐUỔI">Tránh mua đuổi</option>
        </select>

        <select id="minScore">
          <option value="0">Điểm tối thiểu</option>
          <option value="70">Từ 70</option>
          <option value="80">Từ 80</option>
          <option value="85">Từ 85</option>
          <option value="90">Từ 90</option>
        </select>

        <select id="sort">
          <option value="score">Điểm cao nhất</option>
          <option value="vicLeap">Bước nhảy VIC</option>
          <option value="money">Dòng tiền mạnh</option>
          <option value="change20">Tăng 20 phiên</option>
          <option value="rs20">Mạnh hơn VNINDEX</option>
          <option value="risk">Rủi ro thấp</option>
        </select>
      </div>
    </section>

    <section class="layout">
      <div class="cards" id="cards"></div>
      <aside class="detail" id="detail"></aside>
    </section>

    <div class="footer">
      Disclaimer: Dashboard chỉ dùng để sàng lọc tín hiệu kỹ thuật, không phải khuyến nghị mua bán. Cần kết hợp quản trị rủi ro và phân tích cơ bản.
    </div>
  </main>

  <script>
    const DATA_URL = "./data.json?t=";

    const tabs = [
      "Top cơ hội",
      "Bước nhảy VIC",
      "Breakout 20 phiên",
      "Breakout 60 phiên",
      "Breakout 120 phiên",
      "Pullback MA20",
      "Pullback MA50",
      "Dòng tiền mạnh",
      "MACD đảo chiều",
      "RSI hồi phục",
      "Tích lũy nền",
      "An toàn",
      "Tất cả mã"
    ];

    let stocks = [];
    let activeTab = "Bước nhảy VIC";
    let selectedSymbol = null;

    function formatNumber(n, digits = 2) {
      if (n === null || n === undefined || Number.isNaN(Number(n))) return "-";
      return Number(n).toLocaleString("vi-VN", { maximumFractionDigits: digits });
    }

    function renderTabs() {
      document.getElementById("tabs").innerHTML = tabs.map(tab => `
        <button class="tab ${tab === activeTab ? "active" : ""}" onclick="setTab('${tab}')">
          ${tab}
        </button>
      `).join("");
    }

    function renderIndustryOptions() {
      const select = document.getElementById("industry");
      const current = select.value || "all";
      const industries = [...new Set(stocks.map(x => x.industry).filter(Boolean))].sort();

      select.innerHTML =
        `<option value="all">Tất cả ngành</option>` +
        industries.map(x => `<option value="${x}">${x}</option>`).join("");

      if ([...select.options].some(o => o.value === current)) select.value = current;
    }

    function getFiltered() {
      const search = document.getElementById("search").value.toLowerCase().trim();
      const industry = document.getElementById("industry").value;
      const action = document.getElementById("action").value;
      const minScore = Number(document.getElementById("minScore").value);
      const sort = document.getElementById("sort").value;

      let data = stocks.filter(s => {
        const categories = s.categories || [];
        const matchTab = activeTab === "Tất cả mã" || categories.includes(activeTab);

        const matchSearch =
          !search ||
          String(s.symbol || "").toLowerCase().includes(search) ||
          String(s.name || "").toLowerCase().includes(search) ||
          String(s.industry || "").toLowerCase().includes(search);

        const matchIndustry = industry === "all" || s.industry === industry;
        const matchAction = action === "all" || s.action === action;
        const matchScore = Number(s.score || 0) >= minScore;

        return matchTab && matchSearch && matchIndustry && matchAction && matchScore;
      });

      data.sort((a, b) => {
        if (sort === "score") return Number(b.score || 0) - Number(a.score || 0);
        if (sort === "vicLeap") return Number(b.scoreParts?.vicLeap || 0) - Number(a.scoreParts?.vicLeap || 0);
        if (sort === "money") return Number(b.scoreParts?.money || 0) - Number(a.scoreParts?.money || 0);
        if (sort === "change20") return Number(b.change20 || 0) - Number(a.change20 || 0);
        if (sort === "rs20") return Number(b.rs20 || 0) - Number(a.rs20 || 0);
        if (sort === "risk") return Number(b.scoreParts?.risk || 0) - Number(a.scoreParts?.risk || 0);
        return Number(b.score || 0) - Number(a.score || 0);
      });

      return data;
    }

    function renderCards() {
      const data = getFiltered();
      const cards = document.getElementById("cards");

      if (!data.length) {
        cards.innerHTML = `<div class="empty">Không có mã phù hợp bộ lọc hiện tại.</div>`;
        renderDetail(null);
        return;
      }

      if (!selectedSymbol || !data.find(x => x.symbol === selectedSymbol)) {
        selectedSymbol = data[0].symbol;
      }

      cards.innerHTML = data.map(s => {
        const score = Number(s.score || 0);
        const vicScore = Number(s.scoreParts?.vicLeap || 0);

        return `
          <article class="card ${s.symbol === selectedSymbol ? "active" : ""}" onclick="selectStock('${s.symbol}')">
            <div class="head">
              <div>
                <h2 class="symbol">${s.symbol}</h2>
                <div class="company">${s.name || s.symbol} · ${s.industry || "Chưa phân ngành"}</div>
              </div>
              <div>
                <div class="badge">${score}/100</div>
                <div class="badge vic">VIC ${vicScore}/15</div>
              </div>
            </div>

            <div class="bar"><span style="width:${Math.min(score, 100)}%"></span></div>

            <div class="action">${s.action || "THEO DÕI"}</div>

            <div class="desc">
              <b>Setup:</b> ${s.setup || "Theo dõi"}.
              Giá ${formatNumber(s.price)}, RSI ${formatNumber(s.rsi)},
              20 phiên ${formatNumber(s.change20)}%,
              Vol ${formatNumber(s.volumeRatio20)}x TB20.
            </div>

            <div class="metrics">
              <div class="box"><div class="label">Giá</div><div class="value">${formatNumber(s.price)}</div></div>
              <div class="box"><div class="label">RSI</div><div class="value">${formatNumber(s.rsi)}</div></div>
              <div class="box"><div class="label">20 phiên</div><div class="value">${formatNumber(s.change20)}%</div></div>
              <div class="box"><div class="label">Vol</div><div class="value">${formatNumber(s.volumeRatio20)}x</div></div>
            </div>

            <div class="scores">
              <div class="box"><div class="label">Trend</div><div class="value">${s.scoreParts?.trend ?? "-"}</div></div>
              <div class="box"><div class="label">Mom</div><div class="value">${s.scoreParts?.momentum ?? "-"}</div></div>
              <div class="box"><div class="label">Money</div><div class="value">${s.scoreParts?.money ?? "-"}</div></div>
              <div class="box"><div class="label">Setup</div><div class="value">${s.scoreParts?.setup ?? "-"}</div></div>
              <div class="box"><div class="label">VIC Leap</div><div class="value">${s.scoreParts?.vicLeap ?? "-"}</div></div>
              <div class="box"><div class="label">Risk</div><div class="value">${s.scoreParts?.risk ?? "-"}</div></div>
            </div>

            <div class="tags">
              ${(s.categories || []).slice(0, 5).map(c => `
                <span class="tag ${c === "Bước nhảy VIC" || c === "Top cơ hội" ? "hot" : ""}">${c}</span>
              `).join("")}
            </div>
          </article>
        `;
      }).join("");

      renderDetail(stocks.find(x => x.symbol === selectedSymbol));
    }

    function renderDetail(s) {
      const detail = document.getElementById("detail");

      if (!s) {
        detail.innerHTML = `<h2 class="detail-symbol">---</h2><div class="company">Chưa chọn mã</div>`;
        return;
      }

      const score = Number(s.score || 0);

      detail.innerHTML = `
        <div class="head">
          <div>
            <h2 class="detail-symbol">${s.symbol}</h2>
            <div class="company">${s.name || s.symbol} · ${s.industry || "Chưa phân ngành"}</div>
          </div>
          <div class="badge">${score}/100</div>
        </div>

        <div class="bar"><span style="width:${Math.min(score, 100)}%"></span></div>

        <div class="section">
          <h3>Kết luận</h3>
          <div class="desc">
            <b>${s.action || "THEO DÕI"}</b> · Setup: <b>${s.setup || "Theo dõi"}</b> ·
            Market state: ${s.marketState || "-"}.
            Điểm VIC Leap: <b>${s.scoreParts?.vicLeap ?? "-"}/15</b>.
          </div>
        </div>

        <div class="section">
          <h3>Điểm thành phần</h3>
          <div class="scores">
            <div class="box"><div class="label">Trend</div><div class="value">${s.scoreParts?.trend ?? "-"}</div></div>
            <div class="box"><div class="label">Momentum</div><div class="value">${s.scoreParts?.momentum ?? "-"}</div></div>
            <div class="box"><div class="label">Money</div><div class="value">${s.scoreParts?.money ?? "-"}</div></div>
            <div class="box"><div class="label">Setup</div><div class="value">${s.scoreParts?.setup ?? "-"}</div></div>
            <div class="box"><div class="label">VIC Leap</div><div class="value">${s.scoreParts?.vicLeap ?? "-"}</div></div>
            <div class="box"><div class="label">Risk</div><div class="value">${s.scoreParts?.risk ?? "-"}</div></div>
          </div>
        </div>

        <div class="section">
          <h3>Chỉ báo chính</h3>
          <div class="scores">
            <div class="box"><div class="label">MA20</div><div class="value">${formatNumber(s.ma20)}</div></div>
            <div class="box"><div class="label">MA50</div><div class="value">${formatNumber(s.ma50)}</div></div>
            <div class="box"><div class="label">MA100</div><div class="value">${formatNumber(s.ma100)}</div></div>
            <div class="box"><div class="label">MACD</div><div class="value">${formatNumber(s.macd)}</div></div>
            <div class="box"><div class="label">Signal</div><div class="value">${formatNumber(s.macdSignal)}</div></div>
            <div class="box"><div class="label">Hist</div><div class="value">${formatNumber(s.macdHistogram)}</div></div>
          </div>
        </div>

        <div class="section">
          <h3>Tín hiệu tích cực</h3>
          ${(s.positives || []).length
            ? s.positives.map(x => `<div class="good">✅ ${x}</div>`).join("")
            : `<div class="neutral">Chưa có tín hiệu nổi bật.</div>`
          }
        </div>

        <div class="section">
          <h3>Rủi ro cần lưu ý</h3>
          ${(s.risks || []).length
            ? s.risks.map(x => `<div class="risk">⚠️ ${x}</div>`).join("")
            : `<div class="neutral">Chưa ghi nhận rủi ro kỹ thuật lớn.</div>`
          }
        </div>
      `;
    }

    function setTab(tab) {
      activeTab = tab;
      renderTabs();
      renderCards();
    }

    function selectStock(symbol) {
      selectedSymbol = symbol;
      renderCards();
    }

    async function loadData() {
      try {
        const res = await fetch(DATA_URL + Date.now());
        const json = await res.json();

        stocks = json.data || [];

        const updated = json.updatedAt
          ? new Date(json.updatedAt).toLocaleString("vi-VN")
          : "Không rõ";

        document.getElementById("updatedAt").textContent =
          `Cập nhật: ${updated} · ${stocks.length} mã`;

        renderIndustryOptions();
        renderCards();
      } catch (err) {
        console.error(err);
        document.getElementById("updatedAt").textContent = "Không tải được data.json";
      }
    }

    ["search", "industry", "action", "minScore", "sort"].forEach(id => {
      document.getElementById(id).addEventListener("input", renderCards);
      document.getElementById(id).addEventListener("change", renderCards);
    });

    renderTabs();
    loadData();
    setInterval(loadData, 60000);
  </script>
</body>
</html>
'''

files["scripts/scan.js"] = r'''import fs from "fs";
import axios from "axios";
import { SMA, RSI, MACD } from "technicalindicators";

const API_KEY = process.env.VNSTOCK_API_KEY;
const BASE_URL = process.env.VNSTOCK_BASE_URL || "https://api.vnstock.vn";
const OHLCV_URL = process.env.VNSTOCK_OHLCV_URL || "";

const SYMBOLS = (process.env.SYMBOLS || [
  "VIC", "VHM", "VRE",
  "FPT", "MWG", "DGW", "FOX",
  "HPG", "HSG", "NKG",
  "SSI", "HCM", "VCI", "VND", "SHS",
  "BID", "CTG", "VCB", "TCB", "MBB", "ACB", "STB", "VPB", "HDB",
  "PVD", "PVS", "GAS", "BSR", "PLX",
  "GEX", "REE", "PC1", "HDG",
  "KBC", "IDC", "SZC", "BCM",
  "VNM", "MSN", "SAB",
  "GMD", "HAH", "VSC",
  "DGC", "CSV", "DDV",
  "CTR", "CMG", "ELC"
].join(",")).split(",").map(x => x.trim()).filter(Boolean);

const COMPANY_INFO = {
  VIC: { name: "Tập đoàn Vingroup", industry: "Bất động sản / Holding" },
  VHM: { name: "Vinhomes", industry: "Bất động sản" },
  VRE: { name: "Vincom Retail", industry: "Bất động sản bán lẻ" },
  FPT: { name: "FPT Corporation", industry: "Công nghệ" },
  MWG: { name: "Thế Giới Di Động", industry: "Bán lẻ" },
  DGW: { name: "Digiworld", industry: "Bán lẻ / Phân phối" },
  FOX: { name: "FPT Telecom", industry: "Công nghệ / Viễn thông" },
  HPG: { name: "Hòa Phát", industry: "Thép" },
  HSG: { name: "Hoa Sen", industry: "Thép" },
  NKG: { name: "Nam Kim", industry: "Thép" },
  SSI: { name: "Chứng khoán SSI", industry: "Chứng khoán" },
  HCM: { name: "Chứng khoán HSC", industry: "Chứng khoán" },
  VCI: { name: "Chứng khoán Vietcap", industry: "Chứng khoán" },
  VND: { name: "Chứng khoán VNDirect", industry: "Chứng khoán" },
  SHS: { name: "Chứng khoán Sài Gòn Hà Nội", industry: "Chứng khoán" },
  BID: { name: "BIDV", industry: "Ngân hàng" },
  CTG: { name: "VietinBank", industry: "Ngân hàng" },
  VCB: { name: "Vietcombank", industry: "Ngân hàng" },
  TCB: { name: "Techcombank", industry: "Ngân hàng" },
  MBB: { name: "MB Bank", industry: "Ngân hàng" },
  ACB: { name: "ACB", industry: "Ngân hàng" },
  STB: { name: "Sacombank", industry: "Ngân hàng" },
  VPB: { name: "VPBank", industry: "Ngân hàng" },
  HDB: { name: "HDBank", industry: "Ngân hàng" },
  PVD: { name: "PV Drilling", industry: "Dầu khí" },
  PVS: { name: "PVS", industry: "Dầu khí" },
  GAS: { name: "PV Gas", industry: "Dầu khí" },
  BSR: { name: "Lọc hóa dầu Bình Sơn", industry: "Dầu khí" },
  PLX: { name: "Petrolimex", industry: "Dầu khí" },
  GEX: { name: "Gelex", industry: "Công nghiệp" },
  REE: { name: "REE Corp", industry: "Điện / Cơ điện lạnh" },
  PC1: { name: "PC1 Group", industry: "Xây lắp điện" },
  HDG: { name: "Hà Đô", industry: "Bất động sản / Năng lượng" },
  KBC: { name: "Kinh Bắc", industry: "Bất động sản KCN" },
  IDC: { name: "IDICO", industry: "Bất động sản KCN" },
  SZC: { name: "Sonadezi Châu Đức", industry: "Bất động sản KCN" },
  BCM: { name: "Becamex", industry: "Bất động sản KCN" },
  VNM: { name: "Vinamilk", industry: "Thực phẩm" },
  MSN: { name: "Masan", industry: "Tiêu dùng" },
  SAB: { name: "Sabeco", industry: "Đồ uống" },
  GMD: { name: "Gemadept", industry: "Cảng biển / Logistics" },
  HAH: { name: "Hải An", industry: "Vận tải biển" },
  VSC: { name: "Viconship", industry: "Cảng biển" },
  DGC: { name: "Hóa chất Đức Giang", industry: "Hóa chất" },
  CSV: { name: "Hóa chất Cơ bản Miền Nam", industry: "Hóa chất" },
  DDV: { name: "DAP Vinachem", industry: "Hóa chất" },
  CTR: { name: "Viettel Construction", industry: "Viễn thông / Hạ tầng" },
  CMG: { name: "CMC Corp", industry: "Công nghệ" },
  ELC: { name: "ELCOM", industry: "Công nghệ" }
};

function last(arr, n = 1) {
  if (!arr || arr.length < n) return null;
  return arr[arr.length - n];
}

function avg(arr) {
  if (!arr || !arr.length) return 0;
  return arr.reduce((a, b) => a + Number(b || 0), 0) / arr.length;
}

function pct(current, past) {
  if (!past || Number(past) === 0) return 0;
  return ((Number(current) - Number(past)) / Number(past)) * 100;
}

function clamp(v, min, max) {
  return Math.max(min, Math.min(max, v));
}

function highest(arr) {
  const valid = arr.filter(x => Number.isFinite(Number(x))).map(Number);
  return valid.length ? Math.max(...valid) : 0;
}

function lowest(arr) {
  const valid = arr.filter(x => Number.isFinite(Number(x))).map(Number);
  return valid.length ? Math.min(...valid) : 0;
}

function normalizeOHLCV(raw) {
  const rows = Array.isArray(raw)
    ? raw
    : raw?.data || raw?.items || raw?.result || raw?.rows || raw?.candles || [];

  return rows.map(x => ({
    time: x.time || x.date || x.tradingDate || x.t || x.timestamp,
    open: Number(x.open ?? x.o ?? x.Open ?? x.OPEN),
    high: Number(x.high ?? x.h ?? x.High ?? x.HIGH),
    low: Number(x.low ?? x.l ?? x.Low ?? x.LOW),
    close: Number(x.close ?? x.c ?? x.Close ?? x.CLOSE ?? x.price),
    volume: Number(x.volume ?? x.v ?? x.Volume ?? x.VOLUME ?? x.totalVolume)
  }))
  .filter(x =>
    Number.isFinite(x.open) &&
    Number.isFinite(x.high) &&
    Number.isFinite(x.low) &&
    Number.isFinite(x.close) &&
    Number.isFinite(x.volume)
  )
  .sort((a, b) => new Date(a.time) - new Date(b.time));
}

async function fetchOHLCV(symbol, limit = 260) {
  if (!API_KEY) {
    throw new Error("Missing VNSTOCK_API_KEY");
  }

  const headers = {
    Authorization: `Bearer ${API_KEY}`,
    "x-api-key": API_KEY
  };

  let urls = [];

  if (OHLCV_URL) {
    urls.push(
      OHLCV_URL
        .replace("{symbol}", encodeURIComponent(symbol))
        .replace("{ticker}", encodeURIComponent(symbol))
        .replace("{limit}", String(limit))
    );
  } else {
    urls = [
      `${BASE_URL}/ohlcv`,
      `${BASE_URL}/api/ohlcv`,
      `${BASE_URL}/api/v1/ohlcv`,
      `${BASE_URL}/stock/ohlcv`,
      `${BASE_URL}/api/v1/stock/ohlcv`
    ];
  }

  let lastError = null;

  for (const url of urls) {
    try {
      const res = await axios.get(url, {
        headers,
        params: OHLCV_URL ? {} : {
          symbol,
          ticker: symbol,
          timeframe: "1D",
          interval: "1D",
          resolution: "1D",
          limit
        },
        timeout: 25000
      });

      const data = normalizeOHLCV(res.data);

      if (data.length >= 120) {
        return data.slice(-limit);
      }

      lastError = new Error(`Data length ${data.length} < 120`);
    } catch (err) {
      lastError = err;
    }
  }

  throw new Error(`Cannot fetch OHLCV for ${symbol}: ${lastError?.message || "unknown"}`);
}

function calculateIndicators(ohlcv) {
  const closes = ohlcv.map(x => Number(x.close));
  const highs = ohlcv.map(x => Number(x.high));
  const lows = ohlcv.map(x => Number(x.low));
  const volumes = ohlcv.map(x => Number(x.volume));

  const close = last(closes);
  const volume = last(volumes);

  const ma20Arr = SMA.calculate({ period: 20, values: closes });
  const ma50Arr = SMA.calculate({ period: 50, values: closes });
  const ma100Arr = SMA.calculate({ period: 100, values: closes });

  const rsiArr = RSI.calculate({ period: 14, values: closes });

  const macdArr = MACD.calculate({
    values: closes,
    fastPeriod: 12,
    slowPeriod: 26,
    signalPeriod: 9,
    SimpleMAOscillator: false,
    SimpleMASignal: false
  });

  const ma20 = last(ma20Arr);
  const ma50 = last(ma50Arr);
  const ma100 = last(ma100Arr);

  const rsi = last(rsiArr);
  const rsi10 = last(rsiArr, 10);
  const rsi20 = last(rsiArr, 20);

  const macd = last(macdArr);
  const prevMacd = last(macdArr, 2);

  const macdLine = macd?.MACD ?? null;
  const macdSignal = macd?.signal ?? null;
  const macdHistogram = macd?.histogram ?? null;

  const prevMacdLine = prevMacd?.MACD ?? null;
  const prevMacdSignal = prevMacd?.signal ?? null;
  const prevMacdHistogram = prevMacd?.histogram ?? null;

  const avgVol20 = avg(volumes.slice(-20));
  const avgVol50 = avg(volumes.slice(-50));

  const high20 = highest(highs.slice(-21, -1));
  const high60 = highest(highs.slice(-61, -1));
  const high120 = highest(highs.slice(-121, -1));

  const low20 = lowest(lows.slice(-20));
  const low60 = lowest(lows.slice(-60));
  const low90 = lowest(lows.slice(-90));

  const change5 = pct(close, closes[closes.length - 6]);
  const change20 = pct(close, closes[closes.length - 21]);
  const change60 = pct(close, closes[closes.length - 61]);

  const volumeRatio20 = avgVol20 ? volume / avgVol20 : 0;
  const volumeRatio50 = avgVol50 ? volume / avgVol50 : 0;

  const macdCrossUp =
    prevMacdLine !== null &&
    prevMacdSignal !== null &&
    macdLine !== null &&
    macdSignal !== null &&
    prevMacdLine <= prevMacdSignal &&
    macdLine > macdSignal;

  const macdHistogramTurnPositive =
    prevMacdHistogram !== null &&
    macdHistogram !== null &&
    prevMacdHistogram <= 0 &&
    macdHistogram > 0;

  const baseRange60 = high60 && low60 ? ((high60 - low60) / close) * 100 : 999;
  const baseRange90 = high120 && low90 ? ((high120 - low90) / close) * 100 : 999;

  const aboveMa20 = close > ma20;
  const aboveMa50 = close > ma50;
  const aboveMa100 = close > ma100;

  const maStackBullish = ma20 > ma50 && ma50 > ma100;
  const maTurningUp = ma20 > last(ma20Arr, 5) && ma50 >= last(ma50Arr, 5);

  const breakout20 = close > high20;
  const breakout60 = close > high60;
  const breakout120 = close > high120;

  const pullbackMa20 = close > ma20 && low20 <= ma20 * 1.03;
  const pullbackMa50 = close > ma50 && low60 <= ma50 * 1.04;

  const rsiRecover50 = (rsi10 && rsi10 < 45 && rsi > 50) || (rsi20 && rsi20 < 40 && rsi > 50);
  const rsiHealthy = rsi >= 50 && rsi <= 70;
  const rsiHot = rsi > 75;

  const shakeout =
    lowest(lows.slice(-15)) < ma50 * 0.97 &&
    close > ma50 &&
    rsi > 48;

  const dryVolumeBeforeBreakout =
    avg(volumes.slice(-50, -20)) > 0 &&
    avg(volumes.slice(-20, -5)) < avg(volumes.slice(-50, -20)) * 0.85 &&
    volumeRatio20 > 1.5;

  return {
    close,
    volume,
    ma20,
    ma50,
    ma100,
    rsi,
    macdLine,
    macdSignal,
    macdHistogram,
    volumeRatio20,
    volumeRatio50,
    change5,
    change20,
    change60,
    baseRange60,
    baseRange90,
    aboveMa20,
    aboveMa50,
    aboveMa100,
    maStackBullish,
    maTurningUp,
    breakout20,
    breakout60,
    breakout120,
    pullbackMa20,
    pullbackMa50,
    macdCrossUp,
    macdHistogramTurnPositive,
    rsiRecover50,
    rsiHealthy,
    rsiHot,
    shakeout,
    dryVolumeBeforeBreakout,
    enoughData: closes.length >= 120
  };
}

function scoreStock(symbol, ohlcv, vnindexOhlcv) {
  const i = calculateIndicators(ohlcv);
  if (!i.enoughData) return null;

  let rs20 = 0;
  let rs60 = 0;

  try {
    const closes = ohlcv.map(x => Number(x.close));
    const idxCloses = vnindexOhlcv.map(x => Number(x.close));

    const stock20 = pct(last(closes), closes[closes.length - 21]);
    const index20 = pct(last(idxCloses), idxCloses[idxCloses.length - 21]);

    const stock60 = pct(last(closes), closes[closes.length - 61]);
    const index60 = pct(last(idxCloses), idxCloses[idxCloses.length - 61]);

    rs20 = stock20 - index20;
    rs60 = stock60 - index60;
  } catch {}

  let trend = 0;
  if (i.aboveMa20) trend += 4;
  if (i.aboveMa50) trend += 4;
  if (i.aboveMa100) trend += 4;
  if (i.maStackBullish) trend += 5;
  if (i.maTurningUp) trend += 2;
  if (i.change60 > 20) trend += 1;
  trend = clamp(trend, 0, 20);

  let momentum = 0;
  if (i.rsiHealthy) momentum += 4;
  if (i.rsiRecover50) momentum += 4;
  if (i.macdCrossUp) momentum += 4;
  if (i.macdHistogramTurnPositive) momentum += 2;
  if (i.change20 > 8) momentum += 1;
  momentum = clamp(momentum, 0, 15);

  let money = 0;
  if (i.volumeRatio20 > 1.2) money += 3;
  if (i.volumeRatio20 > 1.5) money += 4;
  if (i.volumeRatio20 > 2.0) money += 4;
  if (i.volumeRatio50 > 1.3) money += 3;
  if (i.change20 > 10 && i.volumeRatio20 > 1.2) money += 4;
  if (i.dryVolumeBeforeBreakout) money += 2;
  money = clamp(money, 0, 20);

  let setup = 0;
  if (i.breakout20) setup += 4;
  if (i.breakout60) setup += 5;
  if (i.breakout120) setup += 3;
  if (i.pullbackMa20) setup += 2;
  if (i.pullbackMa50) setup += 1;
  if (i.shakeout) setup += 2;
  setup = clamp(setup, 0, 15);

  let vicLeap = 0;
  if (i.baseRange60 <= 35 || i.baseRange90 <= 45) vicLeap += 3;
  if (i.breakout60) vicLeap += 3;
  if (i.breakout120) vicLeap += 1;
  if (i.volumeRatio20 >= 1.8) vicLeap += 2;
  if (i.macdCrossUp) vicLeap += 2;
  if (i.macdHistogramTurnPositive) vicLeap += 1;
  if (i.rsiRecover50) vicLeap += 2;
  if (i.aboveMa20 && i.aboveMa50 && i.aboveMa100) vicLeap += 1;
  if (rs20 > 5 || rs60 > 10) vicLeap += 1;
  if (i.shakeout) vicLeap += 1;
  if (i.dryVolumeBeforeBreakout) vicLeap += 1;
  vicLeap = clamp(vicLeap, 0, 15);

  let risk = 10;
  if (i.rsiHot) risk -= 3;
  if (i.change20 > 25) risk -= 3;
  if (i.close > i.ma20 * 1.15) risk -= 2;
  if (i.volumeRatio20 > 4) risk -= 1;
  if (i.close < i.ma50) risk -= 2;
  risk = clamp(risk, 0, 10);

  let relativeStrength = 0;
  if (rs20 > 0) relativeStrength += 2;
  if (rs20 > 5) relativeStrength += 2;
  if (rs60 > 10) relativeStrength += 1;
  relativeStrength = clamp(relativeStrength, 0, 5);

  const score = Math.round(trend + momentum + money + setup + vicLeap + risk + relativeStrength);

  const categories = [];
  if (score >= 85) categories.push("Top cơ hội");
  if (vicLeap >= 11) categories.push("Bước nhảy VIC");
  if (i.breakout20) categories.push("Breakout 20 phiên");
  if (i.breakout60) categories.push("Breakout 60 phiên");
  if (i.breakout120) categories.push("Breakout 120 phiên");
  if (i.pullbackMa20) categories.push("Pullback MA20");
  if (i.pullbackMa50) categories.push("Pullback MA50");
  if (money >= 14) categories.push("Dòng tiền mạnh");
  if (i.macdCrossUp || i.macdHistogramTurnPositive) categories.push("MACD đảo chiều");
  if (i.rsiRecover50) categories.push("RSI hồi phục");
  if (i.baseRange60 <= 35 || i.baseRange90 <= 45) categories.push("Tích lũy nền");
  if (risk >= 8 && score >= 75) categories.push("An toàn");
  categories.push("Tất cả mã");

  const positives = [];
  const risks = [];

  if (i.aboveMa20 && i.aboveMa50 && i.aboveMa100) positives.push("Giá nằm trên MA20, MA50 và MA100, cấu trúc xu hướng tích cực.");
  if (i.maStackBullish) positives.push("MA20 > MA50 > MA100, xu hướng tăng đang được xác nhận.");
  if (i.breakout20) positives.push("Giá breakout đỉnh 20 phiên.");
  if (i.breakout60) positives.push("Giá breakout đỉnh 60 phiên, tín hiệu mạnh hơn breakout ngắn hạn.");
  if (i.breakout120) positives.push("Giá breakout đỉnh 120 phiên, thể hiện sức mạnh dài hơn.");
  if (i.volumeRatio20 >= 1.8) positives.push(`Volume tăng mạnh, đạt ${i.volumeRatio20.toFixed(2)} lần trung bình 20 phiên.`);
  if (i.dryVolumeBeforeBreakout) positives.push("Có dấu hiệu volume cạn trước đó rồi bùng lên, giống pha gom hàng trước breakout.");
  if (i.macdCrossUp) positives.push("MACD cắt lên Signal, động lượng có dấu hiệu đảo chiều tăng.");
  if (i.macdHistogramTurnPositive) positives.push("MACD Histogram chuyển từ âm sang dương.");
  if (i.rsiRecover50) positives.push("RSI hồi từ vùng yếu và vượt lại mốc 50, tương tự vùng đánh dấu trên mẫu VIC.");
  if (i.shakeout) positives.push("Có dấu hiệu rũ bỏ dưới MA50 rồi kéo lại nhanh, phù hợp mẫu shakeout trước nhịp tăng.");
  if (rs20 > 5) positives.push(`Sức mạnh tương đối tốt hơn VNINDEX khoảng ${rs20.toFixed(2)}% trong 20 phiên.`);
  if (vicLeap >= 13) positives.push("Mẫu hình đạt VIC Leap rất cao: tích lũy, breakout, dòng tiền và động lượng cùng xác nhận.");
  else if (vicLeap >= 11) positives.push("Mẫu hình có nhiều đặc điểm tương đồng pha bước nhảy của VIC.");

  if (i.rsiHot) risks.push("RSI đang ở vùng nóng, hạn chế mua đuổi tỷ trọng lớn.");
  if (i.change20 > 25) risks.push("Giá đã tăng mạnh trong 20 phiên, rủi ro rung lắc ngắn hạn cao hơn.");
  if (i.close > i.ma20 * 1.15) risks.push("Giá cách xa MA20, nên ưu tiên chờ nhịp kiểm định hoặc rung lắc.");
  if (i.close < i.ma50) risks.push("Giá vẫn dưới MA50, xu hướng trung hạn chưa thật sự xác nhận.");
  if (!risks.length) risks.push("Chưa có rủi ro kỹ thuật lớn, nhưng vẫn cần quản trị điểm cắt lỗ.");

  let action = "THEO DÕI";
  if (score >= 88 && risk >= 7 && vicLeap >= 10) action = "MUA TỪNG PHẦN";
  else if (score >= 80 && risk >= 6) action = "CHỜ ĐIỂM MUA";
  else if (i.rsiHot || i.close > i.ma20 * 1.15) action = "TRÁNH MUA ĐUỔI";

  let setupName = "Theo dõi";
  if (vicLeap >= 13) setupName = "Bước nhảy mạnh giống VIC";
  else if (vicLeap >= 11) setupName = "Bước nhảy tiềm năng";
  else if (i.breakout120) setupName = "Breakout 120 phiên";
  else if (i.breakout60) setupName = "Breakout 60 phiên";
  else if (i.breakout20) setupName = "Breakout 20 phiên";
  else if (i.pullbackMa20) setupName = "Pullback MA20";
  else if (i.pullbackMa50) setupName = "Pullback MA50";
  else if (i.baseRange60 <= 35) setupName = "Tích lũy nền";

  const info = COMPANY_INFO[symbol] || {};

  return {
    symbol,
    name: info.name || symbol,
    industry: info.industry || "Chưa phân ngành",
    price: Number(i.close?.toFixed?.(2) ?? i.close),
    volume: i.volume,
    rsi: Number(i.rsi?.toFixed?.(2) ?? i.rsi),
    macd: Number(i.macdLine?.toFixed?.(4) ?? i.macdLine),
    macdSignal: Number(i.macdSignal?.toFixed?.(4) ?? i.macdSignal),
    macdHistogram: Number(i.macdHistogram?.toFixed?.(4) ?? i.macdHistogram),
    ma20: Number(i.ma20?.toFixed?.(2) ?? i.ma20),
    ma50: Number(i.ma50?.toFixed?.(2) ?? i.ma50),
    ma100: Number(i.ma100?.toFixed?.(2) ?? i.ma100),
    change5: Number(i.change5?.toFixed?.(2) ?? i.change5),
    change20: Number(i.change20?.toFixed?.(2) ?? i.change20),
    change60: Number(i.change60?.toFixed?.(2) ?? i.change60),
    volumeRatio20: Number(i.volumeRatio20?.toFixed?.(2) ?? i.volumeRatio20),
    volumeRatio50: Number(i.volumeRatio50?.toFixed?.(2) ?? i.volumeRatio50),
    rs20: Number(rs20?.toFixed?.(2) ?? rs20),
    rs60: Number(rs60?.toFixed?.(2) ?? rs60),
    score,
    action,
    setup: setupName,
    marketState: trend >= 16 ? "Uptrend mạnh" : trend >= 12 ? "Uptrend" : "Chưa xác nhận",
    scoreParts: {
      trend,
      momentum,
      money,
      setup,
      vicLeap,
      risk,
      relativeStrength
    },
    categories,
    positives,
    risks
  };
}

async function main() {
  if (!API_KEY) {
    throw new Error("Thiếu VNSTOCK_API_KEY. Hãy thêm API key vào GitHub Secrets.");
  }

  console.log("Fetching VNINDEX...");
  const vnindexOhlcv = await fetchOHLCV("VNINDEX", 260);

  const results = [];

  for (const symbol of SYMBOLS) {
    try {
      console.log(`Scanning ${symbol}...`);
      const ohlcv = await fetchOHLCV(symbol, 260);
      const scored = scoreStock(symbol, ohlcv, vnindexOhlcv);

      if (scored) results.push(scored);

      await new Promise(resolve => setTimeout(resolve, 300));
    } catch (err) {
      console.error(`Error ${symbol}:`, err.message);
    }
  }

  results.sort((a, b) => b.score - a.score);

  const output = {
    updatedAt: new Date().toISOString(),
    count: results.length,
    data: results
  };

  fs.writeFileSync("data.json", JSON.stringify(output, null, 2), "utf8");
  console.log(`Done. Wrote ${results.length} stocks to data.json`);
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
'''

files[".github/workflows/update-data.yml"] = r'''name: Update Stock Radar Data

on:
  workflow_dispatch:
  schedule:
    - cron: "*/15 * * * *"

permissions:
  contents: write

jobs:
  update-data:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 20

      - name: Install dependencies
        run: npm install

      - name: Run scanner
        env:
          VNSTOCK_API_KEY: ${{ secrets.VNSTOCK_API_KEY }}
          VNSTOCK_BASE_URL: ${{ secrets.VNSTOCK_BASE_URL }}
          VNSTOCK_OHLCV_URL: ${{ secrets.VNSTOCK_OHLCV_URL }}
          SYMBOLS: ${{ secrets.SYMBOLS }}
        run: npm run scan

      - name: Commit updated data
        run: |
          git config user.name "stock-radar-bot"
          git config user.email "stock-radar-bot@users.noreply.github.com"
          git add data.json
          git diff --staged --quiet || git commit -m "Update stock radar data"
          git push
'''

files["README.md"] = r'''# VN Stock Radar

Dashboard quét cổ phiếu Việt Nam theo tín hiệu kỹ thuật:

- Top cơ hội
- Bước nhảy VIC
- Breakout 20 / 60 / 120 phiên
- Pullback MA20 / MA50
- Dòng tiền mạnh
- MACD đảo chiều
- RSI hồi phục
- Tích lũy nền
- An toàn

## Cách dùng trên GitHub Pages

1. Upload toàn bộ file trong thư mục này lên GitHub repo.
2. Vào Settings → Secrets and variables → Actions.
3. Thêm secrets:

```txt
VNSTOCK_API_KEY = API key VNStock của bạn
VNSTOCK_BASE_URL = Base URL API VNStock
