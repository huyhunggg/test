import axios from "axios";
import { API_KEY, VNSTOCK_ENDPOINTS } from "./config.js";

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

function buildHeaders() {
  return {
    Authorization: `Bearer ${API_KEY}`,
    "x-api-key": API_KEY,
    "X-API-KEY": API_KEY,
    "api-key": API_KEY
  };
}

/**
 * Hàm này hiện chỉ cần VNSTOCK_API_KEY.
 * Không cần VNSTOCK_BASE_URL.
 * Không cần VNSTOCK_OHLCV_URL.
 */
export async function fetchOHLCV(symbol, limit = 260) {
  if (!API_KEY) {
    throw new Error("Missing VNSTOCK_API_KEY");
  }

  const url = VNSTOCK_ENDPOINTS.ohlcv;

  const requestVariants = [
    {
      params: {
        symbol,
        limit,
        timeframe: "1D"
      }
    },
    {
      params: {
        ticker: symbol,
        limit,
        interval: "1D"
      }
    },
    {
      params: {
        code: symbol,
        limit,
        resolution: "1D"
      }
    }
  ];

  let lastError = null;

  for (const variant of requestVariants) {
    try {
      console.log(`Calling VNStock API: ${url} - ${symbol}`);

      const res = await axios.get(url, {
        headers: buildHeaders(),
        params: variant.params,
        timeout: 30000
      });

      const data = normalizeOHLCV(res.data);

      if (data.length >= 120) {
        return data.slice(-limit);
      }

      lastError = new Error(
        `API responded but OHLCV length is ${data.length}. Need at least 120.`
      );
    } catch (err) {
      lastError = err;
    }
  }

  throw new Error(
    `Cannot fetch OHLCV for ${symbol}: ${lastError?.message || "unknown error"}`
  );
}
