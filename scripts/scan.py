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

# Khoảng dữ liệu lịch sử đủ cho MA100, RSI, MACD.
LOOKBACK_DAYS = 460

# VNStock Guest giới hạn 20 request/phút.
# 3.4 giây/request ~ 17.6 request/phút, an toàn hơn quota.
REQUEST_DELAY_SECONDS = 3.4

# Khi VNStock báo quota: chờ khoảng 65 giây để reset quota.
RATE_LIMIT_WAIT_SECONDS = 65

# Không retry nhiều lần, vì retry cũng tính vào quota.
MAX_RETRIES = 1

# Nếu lỗi liên tiếp nhiều mã đầu, dừng sớm.
# Không chạy vô ích toàn bộ hơn 300 mã.
MAX_CONSECUTIVE_FAILURES = 12

# Chỉ cập nhật data.json nếu lấy được ít nhất 30 mã.
# Nếu API lỗi, giữ nguyên data.json cũ để web không trắng.
MIN_VALID_RESULTS = 30


# =========================================================
# HÀM HỖ TRỢ
# =========================================================

def now_utc():
    return datetime.utcnow().isoformat() + "Z"


def safe_float(value, default=0.0):
    try:
        if value is None:
            return default

        return float(str(value).replace(",", "").strip())
    except Exception:
        return default


def clean_symbol(value):
    return str(value).strip().upper()


def load_symbols():
    """
    Đọc danh sách mã từ symbols.txt.

    Chấp nhận:
    - Mỗi dòng một mã
    - Hoặc mã cách nhau bằng dấu phẩy
    """

    if not SYMBOLS_FILE.exists():
        raise FileNotFoundError(
            "Không tìm thấy file symbols.txt ở thư mục gốc repo."
        )

    content = SYMBOLS_FILE.read_text(encoding="utf-8")
    content = content.replace("\n", ",")

    symbols = []

    for raw_symbol in content.split(","):
        stock_symbol = clean_symbol(raw_symbol)

        if not stock_symbol:
            continue

        if stock_symbol.startswith("#"):
            continue

        symbols.append(stock_symbol)

    # Xóa mã trùng nhưng giữ thứ tự.
    return list(dict.fromkeys(symbols))


def normalize_dataframe(df):
    """
    Chuẩn hóa dữ liệu OHLCV từ VNStock.
    """

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("VNStock trả về dữ liệu rỗng.")

    df = df.copy()
    df.columns = [str(column).strip().lower() for column in df.columns]

    column_mapping = {
        "time": "date",
        "datetime": "date",
        "trading_date": "date",
        "tradingdate": "date",
        "date": "date",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume",
        "match_volume": "volume",
        "total_volume": "volume",
    }

    df = df.rename(
        columns={
            old_name: new_name
            for old_name, new_name in column_mapping.items()
            if old_name in df.columns
        }
    )

    required_columns = ["open", "high", "low", "close", "volume"]

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Thiếu cột OHLCV: {missing_columns}. "
            f"Cột hiện có: {list(df.columns)}"
        )

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.sort_values("date")

    for column in required_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.dropna(subset=required_columns).reset_index(drop=True)

    if len(df) < 120:
        raise ValueError(
            f"Không đủ dữ liệu lịch sử: chỉ có {len(df)} phiên."
        )

    return df


def is_rate_limit_error(error):
    error_text = str(error).lower()

    keywords = [
        "maximum api request",
        "request limit",
        "rate limit",
        "20 requests",
        "20/20",
        "wait to retry",
        "quota",
        "giới hạn",
    ]

    return any(keyword in error_text for keyword in keywords)


# =========================================================
# LẤY DỮ LIỆU VNSTOCK
# =========================================================

def fetch_history_once(symbol):
    """
    Vẫn dùng VNStock / VCI.
    """

    end_date = datetime.now()
    start_date = end_date - timedelta(days=LOOKBACK_DAYS)

    quote = Quote(symbol=symbol, source="VCI")

    df = quote.history(
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
        interval="1D",
    )

    return normalize_dataframe(df)


def fetch_history_with_retry(symbol):
    """
    - Nếu quota Guest đầy: chờ reset rồi thử lại 1 lần.
    - Nếu lỗi khác: báo lỗi để main() bỏ qua mã.
    """

    try:
        return fetch_history_once(symbol)

    except BaseException as error:
        # Dùng BaseException để chặn cả trường hợp package
        # VNStock có thể gọi SystemExit khi báo rate-limit.
        if isinstance(error, KeyboardInterrupt):
            raise

        if is_rate_limit_error(error):
            print(
                f"  RATE LIMIT tại {symbol}. "
                f"Chờ {RATE_LIMIT_WAIT_SECONDS} giây để quota reset..."
            )

            time.sleep(RATE_LIMIT_WAIT_SECONDS)

            try:
                return fetch_history_once(symbol)

            except BaseException as retry_error:
                if isinstance(retry_error, KeyboardInterrupt):
                    raise

                raise RuntimeError(
                    f"VNStock vẫn lỗi sau khi chờ quota ở {symbol}: {retry_error}"
                )

        raise RuntimeError(f"Không lấy được dữ liệu {symbol}: {error}")


# =========================================================
# CHỈ BÁO KỸ THUẬT
# =========================================================

def calculate_rsi(close, period=14):
    delta = close.diff()

    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    average_gain = gains.rolling(period).mean()
    average_loss = losses.rolling(period).mean()

    rs = average_gain / average_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    return rsi.fillna(50)


def calculate_macd(close):
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()

    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    histogram = macd - signal

    return macd, signal, histogram


def calculate_change(current, old):
    if not old:
        return 0.0

    return ((current - old) / old) * 100


# =========================================================
# CHẤM ĐIỂM CỔ PHIẾU
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

    change5 = calculate_change(current_price, safe_float(close.iloc[-6]))
    change20 = calculate_change(current_price, safe_float(close.iloc[-21]))
    change60 = calculate_change(current_price, safe_float(close.iloc[-61]))

    average_volume20 = safe_float(volume.tail(20).mean())
    average_volume50 = safe_float(volume.tail(50).mean())

    volume_ratio20 = (
        current_volume / average_volume20
        if average_volume20
        else 0
    )

    volume_ratio50 = (
        current_volume / average_volume50
        if average_volume50
        else 0
    )

    distance_ma20 = (
        ((current_price - ma20) / ma20) * 100
        if ma20
        else 0
    )

    positives = []
    risks = []
    categories = ["Tất cả mã"]

    # -------------------------------
    # Trend: tối đa 20 điểm
    # -------------------------------
    trend_score = 0

    if current_price > ma20:
        trend_score += 5

    if current_price > ma50:
        trend_score += 5

    if current_price > ma100:
        trend_score += 4

    if ma20 > ma50 > ma100:
        trend_score += 6
        positives.append(
            "MA20 > MA50 > MA100, xu hướng tăng đang được xác nhận."
        )

    elif current_price < ma50:
        risks.append(
            "Giá dưới MA50, xu hướng trung hạn chưa xác nhận."
        )

    # -------------------------------
    # Momentum: tối đa 15 điểm
    # -------------------------------
    momentum_score = 0

    if change5 > 0:
        momentum_score += 3

    if change20 > 0:
        momentum_score += 4

    if change60 > 0:
        momentum_score += 3

    if 48 <= current_rsi <= 68:
        momentum_score += 5
        positives.append(
            "RSI trong vùng khỏe, chưa rơi vào trạng thái quá mua."
        )

    elif current_rsi >= 72:
        risks.append(
            f"RSI cao ({current_rsi:.2f}), rủi ro mua đuổi."
        )

    elif current_rsi <= 35:
        risks.append(
            f"RSI thấp ({current_rsi:.2f}), động lượng giá còn yếu."
        )

    # -------------------------------
    # Money: tối đa 20 điểm
    # -------------------------------
    money_score = 0

    if volume_ratio20 >= 1.2:
        money_score += 7

    if volume_ratio20 >= 1.8:
        money_score += 5

    if volume_ratio50 >= 1.2:
        money_score += 4

    if current_price > ma20 and volume_ratio20 >= 1.2:
        money_score += 4
        positives.append(
            "Dòng tiền cải thiện, thanh khoản cao hơn trung bình."
        )

    # -------------------------------
    # Setup: tối đa 15 điểm
    # -------------------------------
    setup_score = 0
    setup_name = "Theo dõi"

    if current_price >= ma20 and -3 <= distance_ma20 <= 5:
        setup_score += 6
        setup_name = "Pullback MA20"
        categories.append("Pullback MA20")

    if ma50 and current_price >= ma50:
        distance_ma50 = abs(current_price - ma50) / ma50

        if distance_ma50 <= 0.05:
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

    # -------------------------------
    # VIC Leap: tối đa 15 điểm
    # -------------------------------
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

    # -------------------------------
    # T+: tối đa 15 điểm
    # -------------------------------
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

    # -------------------------------
    # Risk: tối đa 15 điểm
    # Điểm cao nghĩa là rủi ro thấp.
    # -------------------------------
    risk_score = 15

    if current_rsi >= 72:
        risk_score -= 4

    if distance_ma20 > 10:
        risk_score -= 4
        risks.append(
            f"Giá cao hơn MA20 khoảng {distance_ma20:.2f}%."
        )

    if change20 > 25:
        risk_score -= 3
        risks.append("Giá đã tăng mạnh trong 20 phiên gần đây.")

    if current_price < ma50:
        risk_score -= 2

    if volume_ratio20 < 0.7:
        risk_score -= 2
        risks.append("Thanh khoản hiện tại thấp hơn trung bình 20 phiên.")

    risk_score = max(0, risk_score)

    # -------------------------------
    # Phân nhóm hiển thị
    # -------------------------------
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

    # -------------------------------
    # Tổng điểm và kết luận
    # -------------------------------
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

    market_state = (
        "Uptrend"
        if ma20 > ma50
        else "Chưa xác nhận"
    )

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
# LƯU DỮ LIỆU AN TOÀN
# =========================================================

def save_results_safely(results):
    """
    Không ghi đè data.json nếu kết quả quá ít.
    Ghi qua file tạm để tránh file JSON bị hỏng giữa chừng.
    """

    if len(results) < MIN_VALID_RESULTS:
        print(
            f"KHÔNG LƯU: chỉ có {len(results)} mã hợp lệ. "
            "Giữ nguyên data.json cũ."
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

    print(f"ĐÃ LƯU {len(results)} mã vào data.json")
    return True


# =========================================================
# CHẠY SCANNER
# =========================================================

def main():
    symbols = load_symbols()

    if not symbols:
        raise RuntimeError("symbols.txt không có mã cổ phiếu nào.")

    api_key_exists = bool(os.getenv("VNSTOCK_API_KEY", "").strip())

    print("=" * 60)
    print("VN Stock Radar Scanner")
    print("Nguồn dữ liệu: VNStock / VCI")
    print(f"Tổng số mã: {len(symbols)}")
    print(f"Delay mỗi request: {REQUEST_DELAY_SECONDS}s")
    print(f"VNSTOCK_API_KEY có truyền vào workflow: {api_key_exists}")
    print("=" * 60)

    results = []
    consecutive_failures = 0

    for index, stock_symbol in enumerate(symbols, start=1):
        print(f"\n[{index}/{len(symbols)}] Scanning {stock_symbol}...")

        try:
            dataframe = fetch_history_with_retry(stock_symbol)
            scored_stock = score_stock(stock_symbol, dataframe)

            results.append(scored_stock)
            consecutive_failures = 0

            print(
                f"  OK | score={scored_stock['score']} | "
                f"T+={scored_stock['tplusScore']} | "
                f"{scored_stock['action']}"
            )

        except Exception as error:
            consecutive_failures += 1

            print(
                f"  SKIP {stock_symbol}: "
                f"{type(error).__name__}: {error}"
            )

            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                raise RuntimeError(
                    f"Lỗi liên tiếp {consecutive_failures} mã. "
                    "Dừng sớm để giữ nguyên data.json cũ."
                )

        # Chỉ checkpoint khi đã có đủ dữ liệu hợp lệ.
        if index % 25 == 0 and len(results) >= MIN_VALID_RESULTS:
            print(f"  Checkpoint: {len(results)} mã hợp lệ.")
            save_results_safely(results)

        # Bắt buộc chờ sau mỗi mã để không vượt quota Guest.
        time.sleep(REQUEST_DELAY_SECONDS)

    saved = save_results_safely(results)

    if not saved:
        raise RuntimeError(
            "Scan xong nhưng số mã hợp lệ quá ít. "
            "data.json cũ đã được giữ nguyên."
        )

    print("\nHOÀN TẤT SCAN THỊ TRƯỜNG.")


if __name__ == "__main__":
    try:
        main()

    except Exception as error:
        print("\nFATAL ERROR:")
        print(error)
        traceback.print_exc()
        raise
