import { calculateIndicators } from "./indicators.js";
import { COMPANY_INFO } from "./config.js";
import { last, pct, clamp, round } from "./utils.js";

function calculateRS(stockOhlcv, indexOhlcv) {
  try {
    const stockCloses = stockOhlcv.map(x => Number(x.close));
    const indexCloses = indexOhlcv.map(x => Number(x.close));

    const stock20 = pct(last(stockCloses), stockCloses[stockCloses.length - 21]);
    const index20 = pct(last(indexCloses), indexCloses[indexCloses.length - 21]);

    const stock60 = pct(last(stockCloses), stockCloses[stockCloses.length - 61]);
    const index60 = pct(last(indexCloses), indexCloses[indexCloses.length - 61]);

    return {
      rs20: stock20 - index20,
      rs60: stock60 - index60
    };
  } catch {
    return {
      rs20: 0,
      rs60: 0
    };
  }
}

export function scoreStock(symbol, ohlcv, vnindexOhlcv) {
  const i = calculateIndicators(ohlcv);

  if (!i.enoughData) return null;

  const { rs20, rs60 } = calculateRS(ohlcv, vnindexOhlcv);

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

  /**
   * VIC Leap Score:
   * Nhận diện mẫu có khả năng “bước nhảy” giống VIC:
   * nền tích lũy, breakout, volume bùng, RSI hồi, MACD đảo chiều, RS mạnh.
   */
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

  const score = Math.round(
    trend +
    momentum +
    money +
    setup +
    vicLeap +
    risk +
    relativeStrength
  );

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

  if (i.aboveMa20 && i.aboveMa50 && i.aboveMa100) {
    positives.push("Giá nằm trên MA20, MA50 và MA100, cấu trúc xu hướng tích cực.");
  }

  if (i.maStackBullish) {
    positives.push("MA20 > MA50 > MA100, xu hướng tăng đang được xác nhận.");
  }

  if (i.breakout20) positives.push("Giá breakout đỉnh 20 phiên.");
  if (i.breakout60) positives.push("Giá breakout đỉnh 60 phiên.");
  if (i.breakout120) positives.push("Giá breakout đỉnh 120 phiên.");

  if (i.volumeRatio20 >= 1.8) {
    positives.push(`Volume đạt ${i.volumeRatio20.toFixed(2)} lần trung bình 20 phiên.`);
  }

  if (i.macdCrossUp) positives.push("MACD cắt lên Signal.");
  if (i.macdHistogramTurnPositive) positives.push("MACD Histogram chuyển từ âm sang dương.");

  if (i.rsiRecover50) {
    positives.push("RSI hồi từ vùng yếu và vượt lại mốc 50.");
  }

  if (i.shakeout) {
    positives.push("Có dấu hiệu rũ bỏ dưới MA50 rồi kéo lại nhanh.");
  }

  if (i.dryVolumeBeforeBreakout) {
    positives.push("Có dấu hiệu volume cạn trước đó rồi bùng lên.");
  }

  if (rs20 > 5) {
    positives.push(`Mạnh hơn VNINDEX khoảng ${rs20.toFixed(2)}% trong 20 phiên.`);
  }

  if (vicLeap >= 13) {
    positives.push("VIC Leap rất cao: tích lũy, breakout, dòng tiền và động lượng cùng xác nhận.");
  } else if (vicLeap >= 11) {
    positives.push("Có nhiều đặc điểm tương đồng pha bước nhảy của VIC.");
  }

  if (i.rsiHot) risks.push("RSI đang ở vùng nóng, hạn chế mua đuổi.");
  if (i.change20 > 25) risks.push("Giá đã tăng mạnh trong 20 phiên, rủi ro rung lắc cao.");
  if (i.close > i.ma20 * 1.15) risks.push("Giá cách xa MA20, nên chờ kiểm định hoặc rung lắc.");
  if (i.close < i.ma50) risks.push("Giá vẫn dưới MA50, xu hướng trung hạn chưa xác nhận.");

  if (!risks.length) {
    risks.push("Chưa có rủi ro kỹ thuật lớn, nhưng vẫn cần quản trị điểm cắt lỗ.");
  }

  let action = "THEO DÕI";

  if (score >= 88 && risk >= 7 && vicLeap >= 10) {
    action = "MUA TỪNG PHẦN";
  } else if (score >= 80 && risk >= 6) {
    action = "CHỜ ĐIỂM MUA";
  } else if (i.rsiHot || i.close > i.ma20 * 1.15) {
    action = "TRÁNH MUA ĐUỔI";
  }

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

    price: round(i.close),
    volume: i.volume,
    rsi: round(i.rsi),
    macd: round(i.macdLine, 4),
    macdSignal: round(i.macdSignal, 4),
    macdHistogram: round(i.macdHistogram, 4),

    ma20: round(i.ma20),
    ma50: round(i.ma50),
    ma100: round(i.ma100),

    change5: round(i.change5),
    change20: round(i.change20),
    change60: round(i.change60),

    volumeRatio20: round(i.volumeRatio20),
    volumeRatio50: round(i.volumeRatio50),

    rs20: round(rs20),
    rs60: round(rs60),

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
