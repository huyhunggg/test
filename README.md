# VN Stock Radar

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

## Cấu trúc

```txt
vn-stock-radar/
├── index.html
├── data.json
├── package.json
├── scripts/scan.js
├── src/config.js
├── src/vnstockApi.js
├── src/indicators.js
├── src/scoring.js
├── src/utils.js
└── .github/workflows/update-data.yml
