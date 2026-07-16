import json
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from vnstock.api.quote import Quote


REQUEST_DELAY_SECONDS = 3.6
RATE_LIMIT_WAIT_SECONDS = 65
MAX_RETRIES = 1


def load_symbols():
    try:
        with open("symbols.txt", "r", encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        return [
            "VIC", "VHM", "VRE", "FPT", "HPG", "HCM",
            "SSI", "VCI", "VND", "BID", "CTG", "MBB",
            "TCB", "ACB", "STB", "PVD", "GEX", "KBC"
        ]

    symbols = []

    for line in raw.replace(",", "\n").splitlines():
        s = line.strip().upper()
        if s and not s.startswith("#"):
            symbols.append(s)

    return list(dict.fromkeys(symbols))


SYMBOLS = load_symbols()


def round_num(x, digits=2):
    try:
        if pd.isna(x):
            return None
        return round(float(x), digits)
    except Exception:
        return None


def safe_float(x, default=0):
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default


def pct(current, past):
    try:
        if past is None or past == 0 or pd.isna(past):
            return 0
        return ((current - past) / past) * 100
    except Exception:
        return 0


def rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(series):
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()

    macd_line = ema12 - ema26
    signal = macd_line.ewm(span=9, adjust=False).mean()
    hist = macd_line - signal

    return macd_line, signal, hist


def normalize_df(df):
    df = df.copy()

    rename_map = {
        "time": "time",
        "date": "time",
        "tradingDate": "time",
        "trading_date": "time",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume"
    }

    df = df.rename(columns={c: rename_map.get(c, c) for c in df.columns})

    required = ["open", "high", "low", "close", "volume"]

    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing column {col}. Columns: {list(df.columns)}")

    for col in required:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=required)

    if "time" in df.columns:
        df = df.sort_values("time")

    return df.reset_index(drop=True)


def fetch_history(symbol):
    end = datetime.now()
    start = end - timedelta(days=540)

    q = Quote(symbol=symbol, source="VCI")

    df = q.history(
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        interval="1D"
    )

    df = normalize_df(df)

    if len(df) < 120:
        raise ValueError(f"Not enough data: {len(df)} rows")

    return df.tail(260).reset_index(drop=True)


def is_rate_limit_error(error):
    msg = str(error).lower()
    keywords = [
        "rate limit",
        "request limit",
        "too many requests",
        "maximum api request",
        "giới hạn",
        "20/20",
        "wait to retry",
        "maximum",
        "api request limit"
    ]
    return any(k in msg for k in keywords)


def fetch_history_with_retry(symbol):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fetch_history(symbol)
        except BaseException as e:
            if is_rate_limit_error(e):
                print(f"Rate limit at {symbol}. Wait {RATE_LIMIT_WAIT_SECONDS}s.")
                time.sleep(RATE_LIMIT_WAIT_SECONDS)
            else:
                print(f"Fetch error {symbol}: {e}")
                time.sleep(5)

    raise RuntimeError(f"Failed to fetch {symbol}")


def score_stock(symbol, df):
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    price = close.iloc[-1]

    ma20 = close.rolling(20).mean()
    ma50 = close.rolling(50).mean()
    ma100 = close.rolling(100).mean()

    rsi_series = rsi(close)
    macd_line, macd_signal, macd_hist = macd(close)

    current_ma20 = ma20.iloc[-1]
    current_ma50 = ma50.iloc[-1]
    current_ma100 = ma100.iloc[-1]

    current_rsi = rsi_series.iloc[-1]
    rsi_10 = rsi_series.iloc[-10] if len(rsi_series) >= 10 else np.nan
    rsi_20 = rsi_series.iloc[-20] if len(rsi_series) >= 20 else np.nan

    current_macd = macd_line.iloc[-1]
    current_signal = macd_signal.iloc[-1]
    current_hist = macd_hist.iloc[-1]

    prev_macd = macd_line.iloc[-2]
    prev_signal = macd_signal.iloc[-2]
    prev_hist = macd_hist.iloc[-2]

    avg_vol20 = volume.tail(20).mean()
    avg_vol50 = volume.tail(50).mean()

    volume_ratio20 = volume.iloc[-1] / avg_vol20 if avg_vol20 else 0
    volume_ratio50 = volume.iloc[-1] / avg_vol50 if avg_vol50 else 0

    high20 = high.iloc[-21:-1].max()
    high60 = high.iloc[-61:-1].max()
    high120 = high.iloc[-121:-1].max()

    low20 = low.tail(20).min()
    low60 = low.tail(60).min()
    low90 = low.tail(90).min()

    change5 = pct(price, close.iloc[-6]) if len(close) >= 6 else 0
    change20 = pct(price, close.iloc[-21]) if len(close) >= 21 else 0
    change60 = pct(price, close.iloc[-61]) if len(close) >= 61 else 0

    above_ma20 = price > current_ma20
    above_ma50 = price > current_ma50
    above_ma100 = price > current_ma100

    ma_stack_bullish = current_ma20 > current_ma50 > current_ma100

    try:
        ma_turning_up = current_ma20 > ma20.iloc[-5] and current_ma50 >= ma50.iloc[-5]
    except Exception:
        ma_turning_up = False

    breakout20 = price > high20
    breakout60 = price > high60
    breakout120 = price > high120

    pullback_ma20 = price > current_ma20 and low20 <= current_ma20 * 1.03
    pullback_ma50 = price > current_ma50 and low60 <= current_ma50 * 1.04

    macd_cross_up = prev_macd <= prev_signal and current_macd > current_signal
    hist_turn_positive = prev_hist <= 0 and current_hist > 0
    hist_improving = current_hist > prev_hist

    rsi_recover50 = (
        (not pd.isna(rsi_10) and rsi_10 < 45 and current_rsi > 50) or
        (not pd.isna(rsi_20) and rsi_20 < 40 and current_rsi > 50)
    )

    rsi_healthy = 50 <= current_rsi <= 70
    rsi_hot = current_rsi > 75

    base_range60 = ((high60 - low60) / price) * 100 if price else 999
    base_range90 = ((high120 - low90) / price) * 100 if price else 999

    shakeout = (
        low.tail(15).min() < current_ma50 * 0.97 and
        price > current_ma50 and
        current_rsi > 48
    )

    try:
        dry_volume_before_breakout = (
            volume.iloc[-50:-20].mean() > 0 and
            volume.iloc[-20:-5].mean() < volume.iloc[-50:-20].mean() * 0.85 and
            volume_ratio20 > 1.5
        )
    except Exception:
        dry_volume_before_breakout = False

    trend = 0
    if above_ma20:
        trend += 4
    if above_ma50:
        trend += 4
    if above_ma100:
        trend += 4
    if ma_stack_bullish:
        trend += 5
    if ma_turning_up:
        trend += 2
    if change60 > 20:
        trend += 1
    trend = min(trend, 20)

    momentum = 0
    if rsi_healthy:
        momentum += 4
    if rsi_recover50:
        momentum += 4
    if macd_cross_up:
        momentum += 4
    if hist_turn_positive:
        momentum += 2
    if change20 > 8:
        momentum += 1
    momentum = min(momentum, 15)

    money = 0
    if volume_ratio20 > 1.2:
        money += 3
    if volume_ratio20 > 1.5:
        money += 4
    if volume_ratio20 > 2.0:
        money += 4
    if volume_ratio50 > 1.3:
        money += 3
    if change20 > 10 and volume_ratio20 > 1.2:
        money += 4
    if dry_volume_before_breakout:
        money += 2
    money = min(money, 20)

    setup = 0
    if breakout20:
        setup += 4
    if breakout60:
        setup += 5
    if breakout120:
        setup += 3
    if pullback_ma20:
        setup += 2
    if pullback_ma50:
        setup += 1
    if shakeout:
        setup += 2
    setup = min(setup, 15)

    vic_leap = 0
    if base_range60 <= 35 or base_range90 <= 45:
        vic_leap += 3
    if breakout60:
        vic_leap += 3
    if breakout120:
        vic_leap += 1
    if volume_ratio20 >= 1.8:
        vic_leap += 2
    if macd_cross_up:
        vic_leap += 2
    if hist_turn_positive:
        vic_leap += 1
    if rsi_recover50:
        vic_leap += 2
    if above_ma20 and above_ma50 and above_ma100:
        vic_leap += 1
    if shakeout:
        vic_leap += 1
    if dry_volume_before_breakout:
        vic_leap += 1
    vic_leap = min(vic_leap, 15)

    risk = 10
    if rsi_hot:
        risk -= 3
    if change20 > 25:
        risk -= 3
    if price > current_ma20 * 1.15:
        risk -= 2
    if volume_ratio20 > 4:
        risk -= 1
    if price < current_ma50:
        risk -= 2
    risk = max(0, min(risk, 10))

    relative_strength = 0

    # T+ Score
    tplus = 0

    if above_ma20:
        tplus += 2
    if ma_turning_up:
        tplus += 2
    if 50 <= current_rsi <= 70:
        tplus += 2
    if 0 < change5 <= 10:
        tplus += 2
    if 1.2 <= volume_ratio20 <= 3:
        tplus += 2
    if breakout20 or pullback_ma20:
        tplus += 2
    if current_macd > current_signal or hist_improving:
        tplus += 2
    if risk >= 7:
        tplus += 1

    tplus = min(tplus, 15)

    total_score = round(
        trend +
        momentum +
        money +
        setup +
        vic_leap +
        risk +
        relative_strength
    )

    categories = []

    if total_score >= 85:
        categories.append("Top cơ hội")
    if tplus >= 10:
        categories.append("Lướt sóng T+")
    if vic_leap >= 11:
        categories.append("Bước nhảy VIC")
    if breakout20:
        categories.append("Breakout 20 phiên")
    if breakout60:
        categories.append("Breakout 60 phiên")
    if breakout120:
        categories.append("Breakout 120 phiên")
    if pullback_ma20:
        categories.append("Pullback MA20")
    if pullback_ma50:
        categories.append("Pullback MA50")
    if money >= 14:
        categories.append("Dòng tiền mạnh")
    if macd_cross_up or hist_turn_positive:
        categories.append("MACD đảo chiều")
    if rsi_recover50:
        categories.append("RSI hồi phục")
    if base_range60 <= 35 or base_range90 <= 45:
        categories.append("Tích lũy nền")
    if risk >= 8 and total_score >= 75:
        categories.append("An toàn")

    categories.append("Tất cả mã")

    positives = []
    risks = []

    if tplus >= 12:
        positives.append("Điểm T+ cao: giá trên MA20, RSI khỏe, dòng tiền cải thiện và setup ngắn hạn tốt.")
    elif tplus >= 10:
        positives.append("Có tín hiệu T+ tiềm năng, phù hợp theo dõi điểm mua ngắn hạn.")

    if above_ma20 and above_ma50 and above_ma100:
        positives.append("Giá nằm trên MA20, MA50 và MA100, cấu trúc xu hướng tích cực.")

    if ma_stack_bullish:
        positives.append("MA20 > MA50 > MA100, xu hướng tăng đang được xác nhận.")

    if breakout20:
        positives.append("Giá breakout đỉnh 20 phiên.")

    if breakout60:
        positives.append("Giá breakout đỉnh 60 phiên.")

    if breakout120:
        positives.append("Giá breakout đỉnh 120 phiên.")

    if volume_ratio20 >= 1.8:
        positives.append(f"Volume đạt {volume_ratio20:.2f} lần trung bình 20 phiên.")

    if macd_cross_up:
        positives.append("MACD cắt lên Signal.")

    if hist_turn_positive:
        positives.append("MACD Histogram chuyển từ âm sang dương.")

    if rsi_recover50:
        positives.append("RSI hồi từ vùng yếu và vượt lại mốc 50.")

    if shakeout:
        positives.append("Có dấu hiệu rũ bỏ dưới MA50 rồi kéo lại nhanh.")

    if dry_volume_before_breakout:
        positives.append("Có dấu hiệu volume cạn trước đó rồi bùng lên.")

    if vic_leap >= 13:
        positives.append("VIC Leap rất cao: tích lũy, breakout, dòng tiền và động lượng cùng xác nhận.")
    elif vic_leap >= 11:
        positives.append("Có nhiều đặc điểm tương đồng pha bước nhảy của VIC.")

    if rsi_hot:
        risks.append("RSI đang ở vùng nóng, hạn chế mua đuổi.")
    if change20 > 25:
        risks.append("Giá đã tăng mạnh trong 20 phiên, rủi ro rung lắc cao.")
    if price > current_ma20 * 1.15:
        risks.append("Giá cách xa MA20, nên chờ kiểm định hoặc rung lắc.")
    if price < current_ma50:
        risks.append("Giá vẫn dưới MA50, xu hướng trung hạn chưa xác nhận.")

    if not risks:
        risks.append("Chưa có rủi ro kỹ thuật lớn, nhưng vẫn cần quản trị điểm cắt lỗ.")

    action = "THEO DÕI"

    if rsi_hot or price > current_ma20 * 1.15:
        action = "TRÁNH MUA ĐUỔI"
    elif tplus >= 12 and total_score >= 75 and risk >= 7:
        action = "MUA TỪNG PHẦN"
    elif total_score >= 88 and risk >= 7 and vic_leap >= 10:
        action = "MUA TỪNG PHẦN"
    elif tplus >= 10 and risk >= 6:
        action = "CHỜ ĐIỂM MUA"
    elif total_score >= 80 and risk >= 6:
        action = "CHỜ ĐIỂM MUA"

    setup_name = "Theo dõi"

    if vic_leap >= 13:
        setup_name = "Bước nhảy mạnh giống VIC"
    elif vic_leap >= 11:
        setup_name = "Bước nhảy tiềm năng"
    elif tplus >= 12:
        setup_name = "Lướt sóng T+"
    elif tplus >= 10:
        setup_name = "T+ tiềm năng"
    elif breakout120:
        setup_name = "Breakout 120 phiên"
    elif breakout60:
        setup_name = "Breakout 60 phiên"
    elif breakout20:
        setup_name = "Breakout 20 phiên"
    elif pullback_ma20:
        setup_name = "Pullback MA20"
    elif pullback_ma50:
        setup_name = "Pullback MA50"
    elif base_range60 <= 35:
        setup_name = "Tích lũy nền"

    return {
        "symbol": symbol,
        "name": symbol,
        "industry": "Chưa phân ngành",

        "price": round_num(price),
        "volume": safe_float(volume.iloc[-1]),

        "rsi": round_num(current_rsi),
        "macd": round_num(current_macd, 4),
        "macdSignal": round_num(current_signal, 4),
        "macdHistogram": round_num(current_hist, 4),

        "ma20": round_num(current_ma20),
        "ma50": round_num(current_ma50),
        "ma100": round_num(current_ma100),

        "change5": round_num(change5),
        "change20": round_num(change20),
        "change60": round_num(change60),

        "volumeRatio20": round_num(volume_ratio20),
        "volumeRatio50": round_num(volume_ratio50),

        "rs20": 0,
        "rs60": 0,

        "score": total_score,
        "tplusScore": tplus,
        "action": action,
        "setup": setup_name,
        "marketState": "Uptrend mạnh" if trend >= 16 else "Uptrend" if trend >= 12 else "Chưa xác nhận",

        "scoreParts": {
            "trend": trend,
            "momentum": momentum,
            "money": money,
            "setup": setup,
            "vicLeap": vic_leap,
            "tplus": tplus,
            "risk": risk,
            "relativeStrength": relative_strength
        },

        "categories": categories,
        "positives": positives,
        "risks": risks
    }


def save_results(results):
    results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)

    output = {
        "updatedAt": datetime.utcnow().isoformat() + "Z",
        "count": len(results),
        "data": results
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


def main():
    print("Start scanning market with vnstock Python package...")
    print(f"Total symbols: {len(SYMBOLS)}")
    print(f"Delay per request: {REQUEST_DELAY_SECONDS}s")

    results = []

    for idx, symbol in enumerate(SYMBOLS, start=1):
        try:
            print(f"[{idx}/{len(SYMBOLS)}] Scanning {symbol}...")

            df = fetch_history_with_retry(symbol)
            scored = score_stock(symbol, df)

            if scored:
                results.append(scored)
                print(
                    f"OK {symbol}: score={scored.get('score')} "
                    f"T+={scored.get('tplusScore')} "
                    f"setup={scored.get('setup')}"
                )

            if idx % 10 == 0:
                save_results(results)
                print(f"Checkpoint saved: {len(results)} stocks")

            time.sleep(REQUEST_DELAY_SECONDS)

        except BaseException as e:
            print(f"Skip {symbol}. Error: {e}")
            time.sleep(REQUEST_DELAY_SECONDS)
            continue

    save_results(results)
    print(f"Done. Wrote {len(results)} stocks to data.json")


if __name__ == "__main__":
    main()
