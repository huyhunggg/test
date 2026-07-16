import axios from "axios";
import { API_KEY, BASE_URL, OHLCV_URL } from "./config.js";

export function normalizeOHLCV(raw) {
  const rows = Array.isArray(raw)
    ? raw
    : raw?.data || raw?.items || raw?.result || raw?.rows || raw?.candles || [];

  return rows
    .map(x => ({
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

export async function fetchOHLCV(symbol, limit = 260) {
  if (!API_KEY) {
    throw new Error("Missing VNSTOCK_API_KEY");
  }

  const headers = {
    Authorization: `Bearer ${API_KEY}`,
    "x-api-key": API_KEY
  };

  let urls = [];

  /**
   * Nếu bạn có endpoint chính xác, nên set GitHub Secret:
   *
   * VNSTOCK_OHLCV_URL=https://.../ohlcv?symbol={symbol}&limit={limit}
   *
   * Hoặc:
   *
   * VNSTOCK_OHLCV_URL=https://.../api/v1/candle?symbol={symbol}&interval=1D&limit={limit}
   */
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
        params: OHLCV_URL
          ? {}
          : {
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

  throw new Error(
    `Cannot fetch OHLCV for ${symbol}: ${lastError?.message || "unknown"}`
  );
}
