import { SMA, RSI, MACD } from "technicalindicators";
import { last, avg, pct, highest, lowest } from "./utils.js";

export function calculateIndicators(ohlcv) {
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

  const rsiRecover50 =
    (rsi10 && rsi10 < 45 && rsi > 50) ||
    (rsi20 && rsi20 < 40 && rsi > 50);

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
