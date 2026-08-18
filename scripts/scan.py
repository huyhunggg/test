import json
import os
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from vnstock.api.quote import Quote


# =========================================================
# CẤU HÌNH
# =========================================================

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT_DIR / "data.json"
SYMBOLS_FILE = ROOT_DIR / "symbols.txt"

# Chỉ cần hơn 100 phiên để tính MA100; lấy 460 ngày lịch
# để có đủ dữ liệu sau các ngày nghỉ/lễ mà không quá chậm.
LOOKBACK_DAYS = 460

# Không gọi quá nhanh để hạn chế bị rate-limit.
REQUEST_DELAY_SECONDS = 1.2

# Retry ít lần để không treo hàng giờ khi VNStock lỗi hàng loạt.
MAX_RETRIES = 2
RETRY_WAIT_SECONDS = 5

# Nếu 12 mã đầu đều fail, dừng ngay.
# Không cố quét vài trăm mã lỗi rồi bị GitHub timeout.
MAX_CONSECUTIVE_FAILURES = 12

# Chỉ ghi data.json mới nếu có ít nhất số lượng kết quả này.
# Nếu không đủ, giữ nguyên data.json cũ.
MIN_VALID_RESULTS = 30


# =========================================================
# TIỆN ÍCH
# =========================================================

def now_utc():
    return datetime.utcnow().isoformat() + "Z"


def safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        value = str(value).replace(",", "").strip()
        return float(value)
    except Exception:
        return default


def clean_symbol(symbol):
    return str(symbol).strip().upper()


def load_symbols():
    """
    Thứ tự ưu tiên:
    1. GitHub Secret SYMBOLS: VCB,HPG,FPT...
    2. symbols.txt: mỗi dòng một mã hoặc phân tách bằng dấu phẩy.
    """

    env_symbols = os.getenv("SYMBOLS", "").strip()

    if env_symbols:
        raw = env_symbols.replace("\n", ",").split(",")
        symbols = [clean_symbol(x) for x in raw if clean_symbol(x)]
        return list(dict.fromkeys(symbols))

    if not SYMBOLS_FILE.exists():
        raise FileNotFoundError(
            "Không tìm thấy symbols.txt và GitHub Secret SYMBOLS cũng đang trống."
        )

    content = SYMBOLS_FILE.read_text(encoding="utf-8")
    content = content.replace("\n", ",")
    raw = content.split(",")

    symbols = []
    for item in raw:
        symbol = clean_symbol(item)

        # Bỏ dòng comment.
        if not symbol or symbol.startswith("#"):
            continue

        symbols.append(symbol)

    return list(dict.fromkeys(symbols))


def normalize_df(df):
    """
    Chuẩn hóa cột OHLCV do VNStock có thể trả về tên cột khác nhau.
    """

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("VNStock trả về dữ liệu rỗng.")

    df = df.copy()
    df.columns = [str(col).strip().lower() for col in df.columns]

    rename_map = {
        "time": "date",
        "datetime": "date",
        "tradingdate": "date",
        "trading_date": "date",
        "date": "date",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume",
        "match_volume": "volume",
        "total_volume": "volume",
    }

    df = df.rename(columns={
        old: new for old, new in rename_map.items() if old in df.columns
    })

    required = ["open", "high", "low", "close", "volume"]

    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Thiếu cột OHLCV: {missing}. Columns: {list(df.columns)}")

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.sort_values("date")

    for column in required:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.dropna(subset=required).reset_index(drop=True)

    if len(df) < 120:
        raise ValueError(f"Không đủ lịch sử giá: chỉ có {len(df)} phiên.")

    return df


# =========================================================
# LẤY DỮ LIỆU VNSTOCK
# =========================================================

def fetch_history_once(symbol):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=LOOKBACK_DAYS)

    # Vẫn dùng VNStock + VCI theo đúng hệ thống hiện tại.
    quote = Quote(symbol=symbol, source="VCI")

    df = quote.history(
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
        interval="1D",
    )

    return normalize_df(df)


def fetch_history_with_retry(symbol):
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fetch_history_once(symbol)

        except Exception as error:
            last_error = error

            print(
                f"  Attempt {attempt}/{MAX_RETRIES} failed for {symbol}: "
                f"{type(error).__name__}: {error}"
            )

            if attempt < MAX_RETRIES:
                time.sleep(RETRY_WAIT_SECONDS * attempt)

    raise RuntimeError(f"Failed to fetch {symbol}: {last_error}")


# =========================================================
# CHỈ BÁO KỸ THUẬT
# =========================================================

def calculate_rsi(close, period=14):
    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    return rsi.fillna(50)


def calculate_macd(close):
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()

    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    histogram = macd - signal

    return macd, signal, histogram


def pct_change(current, past):
    if not past:
        return 0.0
    return ((current - past) / past) * 100


# =========================================================
# CHẤM ĐIỂM
# =========================================================

def score_stock(symbol, df):
    close = df["close"]
    volume = df["volume"]

    current_price = safe_float(close.iloc[-1])
    current_volume = safe_float(volume.iloc[-1])

    ma20 = safe_float(close.rolling(20).mean().iloc[-1])
    ma50 = safe_float(close.rolling(50).mean().iloc[-1])
    ma100 = safe_float(close.rolling(100).mean().iloc[-1])

    rsi_series = calculate_rsi(close)
    current_rsi = safe_float(rsi_series.iloc[-1])

    macd_series, signal_series, histogram_series = calculate_macd(close)

    macd = safe_float(macd_series.iloc[-1])
    macd_signal = safe_float(signal_series.iloc[-1])
    macd_histogram = safe_float(histogram_series.iloc[-1])

    change5 = pct_change(current_price, safe_float(close.iloc[-6]))
    change20 = pct_change(current_price, safe_float(close.iloc[-21]))
    change60 = pct_change(current_price, safe_float(close.iloc[-61]))

    avg_volume20 = safe_float(volume.tail(20).mean())
    avg_volume50 = safe_float(volume.tail(50).mean())

    volume_ratio20 = current_volume / avg_volume20 if avg_volume20 else 0
    volume_ratio50 = current_volume / avg_volume50 if avg_volume50 else 0

    positives = []
    risks = []
    categories = ["Tất cả mã"]

    # -----------------------------------------------------
    # Trend: tối đa 20
    # -----------------------------------------------------
    trend_score = 0

    if current_price > ma20:
        trend_score += 5

    if current_price > ma50:
        trend_score += 5

    if current_price > ma100:
        trend_score += 4

    if ma20 > ma50 > ma100:
        trend_score += 6
        positives.append("MA20 > MA50 > MA100, xu hướng tăng đang được xác nhận.")

    elif current_price < ma50:
        risks.append("Giá vẫn dưới MA50, xu hướng trung hạn chưa xác nhận.")

    # -----------------------------------------------------
    # Momentum: tối đa 15
    # -----------------------------------------------------
    momentum_score = 0

    if change5 > 0:
        momentum_score += 3

    if change20 > 0:
        momentum_score += 4

    if change60 > 0:
        momentum_score += 3

    if 48 <= current_rsi <= 68:
        momentum_score += 5
        positives.append("RSI nằm trong vùng khỏe, chưa quá nóng.")

    elif current_rsi >= 72:
        risks.append(f"RSI cao ({current_rsi:.2f}), rủi ro mua đuổi.")

    elif current_rsi <= 35:
        risks.append(f"RSI thấp ({current_rsi:.2f}), xu hướng giá còn yếu.")

    # -----------------------------------------------------
    # Money: tối đa 20
    # -----------------------------------------------------
    money_score = 0

    if volume_ratio20 >= 1.2:
        money_score += 7

    if volume_ratio20 >= 1.8:
        money_score += 5

    if volume_ratio50 >= 1.2:
        money_score += 4

    if current_price > ma20 and volume_ratio20 >= 1.2:
        money_score += 4
        positives.append("Dòng tiền cải thiện, thanh khoản cao hơn trung bình.")

    # -----------------------------------------------------
    # Setup: tối đa 15
    # -----------------------------------------------------
    setup_score = 0
    setup_name = "Theo dõi"

    distance_ma20 = ((current_price - ma20) / ma20) * 100 if ma20 else 0

    if current_price >= ma20 and distance_ma20 <= 5:
        setup_score += 6
        setup_name = "Pullback MA20"
        categories.append("Pullback MA20")

    if current_price >= ma50 and abs(current_price - ma50) / ma50 <= 0.05:
        setup_score += 4
        setup_name = "Pullback MA50"
        categories.append("Pullback MA50")

    high20 = safe_float(df["high"].tail(20).max())

    if current_price >= high20 * 0.985 and volume_ratio20 >= 1.2:
        setup_score += 5
        setup_name = "Breakout 20 phiên"
        categories.append("Breakout 20 phiên")

    high60 = safe_float(df["high"].tail(60).max())

    if current_price >= high60 * 0.985 and volume_ratio20 >= 1.2:
        categories.append("Breakout 60 phiên")

    high120 = safe_float(df["high"].tail(120).max())

    if current_price >= high120 * 0.985 and volume_ratio20 >= 1.2:
        categories.append("Breakout 120 phiên")

    # -----------------------------------------------------
    # VIC Leap: tối đa 15
    # -----------------------------------------------------
    vic_leap_score = 0

    if current_price > ma20:
        vic_leap_score += 3

    if macd_histogram > 0:
        vic_leap_score += 3

    if macd > macd_signal:
        vic_leap_score += 3

    if volume_ratio20 >= 1.3:
        vic_leap_score += 3

    if 45 <= current_rsi <= 70:
        vic_leap_score += 3

    if vic_leap_score >= 8:
        categories.append("Bước nhảy VIC")

    # -----------------------------------------------------
    # T+: tối đa 15
    # -----------------------------------------------------
    tplus_score = 0

    if current_price > ma20:
        tplus_score += 3

    if 47 <= current_rsi <= 68:
        tplus_score += 3

    if volume_ratio20 >= 1.1:
        tplus_score += 3

    if macd_histogram >= 0:
        tplus_score += 3

    if -3 <= distance_ma20 <= 7:
        tplus_score += 3

    if tplus_score >= 9:
        categories.append("Lướt sóng T+")

        positives.append(
            "Điểm T+ tốt: giá gần MA20, RSI phù hợp, "
            "dòng tiền hoặc MACD có cải thiện."
        )

    # -----------------------------------------------------
    # Risk: tối đa 15
    # Điểm cao = rủi ro thấp
    # -----------------------------------------------------
    risk_score = 15

    if current_rsi >= 72:
        risk_score -= 4

    if distance_ma20 > 10:
        risk_score -= 4
        risks.append(f"Giá đang cao hơn MA20 khoảng {distance_ma20:.2f}%.")

    if change20 > 25:
        risk_score -= 3
        risks.append("Giá đã tăng mạnh trong 20 phiên gần đây.")

    if current_price < ma50:
        risk_score -= 2

    if volume_ratio20 < 0.7:
        risk_score -= 2
        risks.append("Thanh khoản hiện tại thấp hơn trung bình 20 phiên.")

    risk_score = max(0, risk_score)

    # -----------------------------------------------------
    # Nhóm Bluechip / Penny đơn giản theo giá.
    # Có thể tùy chỉnh sau.
    # -----------------------------------------------------
    if current_price >= 30:
        categories.append("Bluechip")

    if current_price <= 20:
        categories.append("Penny")

    if volume_ratio20 >= 1.5:
        categories.append("Dòng tiền mạnh")

    if macd_histogram > 0 and macd > macd_signal:
        categories.append("MACD đảo chiều")

    if 45 <= current_rsi <= 55 and macd_histogram >= 0:
        categories.append("RSI hồi phục")

    # -----------------------------------------------------
    # Tổng điểm và hành động
    # -----------------------------------------------------
    total_score = (
        trend_score
        + momentum_score
        + money_score
        + setup_score
        + vic_leap_score
        + tplus_score
        + risk_score
    )

    total_score = min(100, int(round(total_score)))

    if current_rsi >= 75 or distance_ma20 > 12 or change20 > 30:
        action = "TRÁNH MUA ĐUỔI"

    elif (
        tplus_score >= 11
        and 47 <= current_rsi <= 68
        and -3 <= distance_ma20 <= 6
        and volume_ratio20 >= 1.1
    ):
        action = "MUA TỪNG PHẦN"

    elif tplus_score >= 8:
        action = "CHỜ ĐIỂM MUA"

    else:
        action = "THEO DÕI"

    market_state = "Uptrend" if ma20 > ma50 else "Chưa xác nhận"

    return {
        "symbol": symbol,
        "name": symbol,
        "industry": "Chưa phân ngành",

        "price": round(current_price, 2),
        "volume": round(current_volume, 2),

        "rsi": round(current_rsi, 2),
        "macd": round(macd, 4),
        "macdSignal": round(macd_signal, 4),
        "macdHistogram": round(macd_histogram, 4),

        "ma20": round(ma20, 2),
        "ma50": round(ma50, 2),
        "ma100": round(ma100, 2),

        "change5": round(change5, 2),
        "change20": round(change20, 2),
        "change60": round(change60, 2),

        "volumeRatio20": round(volume_ratio20, 2),
        "volumeRatio50": round(volume_ratio50, 2),

        "score": total_score,
        "tplusScore": int(tplus_score),

        "action": action,
        "setup": setup_name,
        "marketState": market_state,

        "scoreParts": {
            "trend": int(trend_score),
            "momentum": int(momentum_score),
            "money": int(money_score),
            "setup": int(setup_score),
            "vicLeap": int(vic_leap_score),
            "tplus": int(tplus_score),
            "risk": int(risk_score),
            "relativeStrength": 0,
        },

        "categories": list(dict.fromkeys(categories)),
        "positives": positives,
        "risks": risks,
        "priceTime": now_utc(),
    }


# =========================================================
# LƯU FILE AN TOÀN
# =========================================================

def save_results_safely(results):
    """
    Chỉ ghi đè khi đủ dữ liệu hợp lệ.
    Ghi qua file .tmp trước để tránh data.json hỏng giữa chừng.
    """

    if len(results) < MIN_VALID_RESULTS:
        print(
            f"NOT SAVING: only {len(results)} valid results. "
            "Existing data.json is kept unchanged."
        )
        return False

    results = sorted(
        results,
        key=lambda item: item.get("score", 0),
        reverse=True,
    )

    output = {
        "updatedAt": now_utc(),
        "count": len(results),
        "data": results,
    }

    temp_file = DATA_FILE.with_suffix(".json.tmp")

    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)

    temp_file.replace(DATA_FILE)

    print(f"SAVED: {len(results)} stocks to {DATA_FILE}")
    return True


# =========================================================
# MAIN
# =========================================================

def main():
    symbols = load_symbols()

    if not symbols:
        raise RuntimeError("Danh sách symbols trống.")

    print("==============================================")
    print("VN Stock Radar Scanner")
    print("Data source: VNStock / VCI")
    print(f"Total symbols: {len(symbols)}")
    print(f"Lookback: {LOOKBACK_DAYS} days")
    print("==============================================")

    results = []
    consecutive_failures = 0

    for index, symbol in enumerate(symbols, start=1):
        print(f"[{index}/{len(symbols)}] Scanning {symbol}...")

        try:
            dataframe = fetch_history_with_retry(symbol)
            scored = score_stock(symbol, dataframe)

            results.append(scored)
            consecutive_failures = 0

            print(
                f"  OK {symbol} | "
                f"score={scored['score']} | "
                f"T+={scored['tplusScore']} | "
                f"action={scored['action']}"
            )

        except Exception as error:
            consecutive_failures += 1

            print(f"  SKIP {symbol}: {type(error).__name__}: {error}")

            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                raise RuntimeError(
                    f"VNStock failed {consecutive_failures} symbols continuously. "
                    "Stop early; existing data.json will not be overwritten."
                )

        # Chỉ checkpoint nếu đã có đủ dữ liệu để file có ý nghĩa.
        if index % 25 == 0 and len(results) >= MIN_VALID_RESULTS:
            print(f"Checkpoint at {index}: {len(results)} valid stocks")
            save_results_safely(results)

        time.sleep(REQUEST_DELAY_SECONDS)

    if not save_results_safely(results):
        raise RuntimeError(
            "Scan completed but valid results are too few. "
            "Existing data.json was preserved."
        )

    print("Scanner completed successfully.")


if __name__ == "__main__":
    try:
        main()

    except Exception as error:
        print("\nFATAL ERROR:")
        print(error)
        traceback.print_exc()

        # Exit code 1 để GitHub Actions báo fail,
        # nhưng data.json cũ vẫn còn nguyên.
        raise
