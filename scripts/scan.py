import json
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from vnstock.api.quote import Quote


# =========================
# CONFIG
# =========================

REQUEST_DELAY_SECONDS = 3.6
RATE_LIMIT_WAIT_SECONDS = 65
MAX_RETRIES = 1

MAX_STALE_DAYS = 14
MIN_AVG_VOL20 = 50000
MIN_RECENT_VOLUME_DAYS = 5

PENNY_MAX_PRICE = 15
PENNY_MIN_AVG_VOL20 = 100000


BLACKLIST_SYMBOLS = {
    # Mã nghi ngờ không còn giao dịch / dữ liệu không đáng tin / mã rác
    "BBC", "XLV",
    "X20", "X26", "X77", "XDH", "XHC", "XMC",
    "WTC", "VTX",

    # Có thể bổ sung thêm nếu bạn thấy mã nào bị lỗi dữ liệu
    "VST", "VSM", "VSI", "VSF", "VSE", "VSA",
    "VQC", "VPS", "VPR", "VPC", "VPA",
    "VNX", "VNP", "VNI", "VNF", "VNB",
    "VMS", "VMB", "VLP", "VLG", "VLA",
    "VTJ", "VTK", "VTL", "VTM", "VTN", "VTR", "VTS",
    "VTG", "VTH", "VTD", "VTE"
}


BLUECHIP_SYMBOLS = {
    # Ngân hàng
    "VCB", "BID", "CTG", "TCB", "MBB", "ACB", "VPB", "STB", "HDB", "VIB", "TPB", "LPB", "EIB", "OCB", "SHB",

    # Bất động sản / Holding
    "VIC", "VHM", "VRE", "BCM", "KDH", "NLG",

    # Công nghệ / Bán lẻ
    "FPT", "MWG", "PNJ", "FRT",

    # Hàng hóa / Công nghiệp
    "HPG", "GAS", "PLX", "POW", "GVR", "REE", "GEX", "DGC",

    # Tiêu dùng
    "MSN", "VNM", "SAB", "MCH", "QNS",

    # Chứng khoán
    "SSI", "HCM", "VCI", "VND", "SHS", "MBS", "FTS", "BSI",

    # Logistics / Hạ tầng / Hàng không
    "GMD", "VJC", "HVN", "ACV", "VTP",

    # Khác
    "BVH", "PVD", "PVS", "BSR"
}


COMPANY_INFO = {
    "ACB": {"name": "ACB", "industry": "Ngân hàng"},
    "BID": {"name": "BIDV", "industry": "Ngân hàng"},
    "CTG": {"name": "VietinBank", "industry": "Ngân hàng"},
    "VCB": {"name": "Vietcombank", "industry": "Ngân hàng"},
    "TCB": {"name": "Techcombank", "industry": "Ngân hàng"},
    "MBB": {"name": "MB Bank", "industry": "Ngân hàng"},
    "VPB": {"name": "VPBank", "industry": "Ngân hàng"},
    "STB": {"name": "Sacombank", "industry": "Ngân hàng"},
    "HDB": {"name": "HDBank", "industry": "Ngân hàng"},
    "VIB": {"name": "VIB", "industry": "Ngân hàng"},
    "TPB": {"name": "TPBank", "industry": "Ngân hàng"},
    "LPB": {"name": "LPBank", "industry": "Ngân hàng"},
    "EIB": {"name": "Eximbank", "industry": "Ngân hàng"},
    "OCB": {"name": "OCB", "industry": "Ngân hàng"},
    "SHB": {"name": "SHB", "industry": "Ngân hàng"},

    "VIC": {"name": "Tập đoàn Vingroup", "industry": "Bất động sản / Holding"},
    "VHM": {"name": "Vinhomes", "industry": "Bất động sản"},
    "VRE": {"name": "Vincom Retail", "industry": "Bất động sản bán lẻ"},
    "KDH": {"name": "Khang Điền", "industry": "Bất động sản"},
    "NLG": {"name": "Nam Long", "industry": "Bất động sản"},
    "DXG": {"name": "Đất Xanh", "industry": "Bất động sản"},
    "DIG": {"name": "DIC Corp", "industry": "Bất động sản"},
    "PDR": {"name": "Phát Đạt", "industry": "Bất động sản"},
    "NVL": {"name": "Novaland", "industry": "Bất động sản"},
    "CEO": {"name": "CEO Group", "industry": "Bất động sản"},

    "KBC": {"name": "Kinh Bắc", "industry": "Bất động sản KCN"},
    "IDC": {"name": "IDICO", "industry": "Bất động sản KCN"},
    "SZC": {"name": "Sonadezi Châu Đức", "industry": "Bất động sản KCN"},
    "BCM": {"name": "Becamex", "industry": "Bất động sản KCN"},
    "LHG": {"name": "Long Hậu", "industry": "Bất động sản KCN"},
    "NTC": {"name": "Nam Tân Uyên", "industry": "Bất động sản KCN"},

    "FPT": {"name": "FPT Corporation", "industry": "Công nghệ"},
    "FOX": {"name": "FPT Telecom", "industry": "Công nghệ / Viễn thông"},
    "CMG": {"name": "CMC Corp", "industry": "Công nghệ"},
    "ELC": {"name": "ELCOM", "industry": "Công nghệ"},
    "CTR": {"name": "Viettel Construction", "industry": "Viễn thông / Hạ tầng"},

    "MWG": {"name": "Thế Giới Di Động", "industry": "Bán lẻ"},
    "DGW": {"name": "Digiworld", "industry": "Bán lẻ / Phân phối"},
    "FRT": {"name": "FPT Retail", "industry": "Bán lẻ"},
    "PNJ": {"name": "Vàng bạc Đá quý Phú Nhuận", "industry": "Bán lẻ / Trang sức"},

    "HPG": {"name": "Hòa Phát", "industry": "Thép"},
    "HSG": {"name": "Hoa Sen", "industry": "Thép"},
    "NKG": {"name": "Nam Kim", "industry": "Thép"},

    "SSI": {"name": "Chứng khoán SSI", "industry": "Chứng khoán"},
    "HCM": {"name": "Chứng khoán HSC", "industry": "Chứng khoán"},
    "VCI": {"name": "Chứng khoán Vietcap", "industry": "Chứng khoán"},
    "VND": {"name": "Chứng khoán VNDirect", "industry": "Chứng khoán"},
    "SHS": {"name": "Chứng khoán Sài Gòn Hà Nội", "industry": "Chứng khoán"},
    "MBS": {"name": "Chứng khoán MB", "industry": "Chứng khoán"},
    "FTS": {"name": "Chứng khoán FPT", "industry": "Chứng khoán"},
    "BSI": {"name": "Chứng khoán BIDV", "industry": "Chứng khoán"},
    "CTS": {"name": "Chứng khoán VietinBank", "industry": "Chứng khoán"},
    "VIX": {"name": "Chứng khoán VIX", "industry": "Chứng khoán"},

    "PVD": {"name": "PV Drilling", "industry": "Dầu khí"},
    "PVS": {"name": "PVS", "industry": "Dầu khí"},
    "GAS": {"name": "PV Gas", "industry": "Dầu khí"},
    "BSR": {"name": "Lọc hóa dầu Bình Sơn", "industry": "Dầu khí"},
    "PLX": {"name": "Petrolimex", "industry": "Dầu khí"},
    "PVT": {"name": "PVTrans", "industry": "Dầu khí / Vận tải"},

    "GEX": {"name": "Gelex", "industry": "Công nghiệp"},
    "REE": {"name": "REE Corp", "industry": "Điện / Cơ điện lạnh"},
    "PC1": {"name": "PC1 Group", "industry": "Xây lắp điện"},
    "HDG": {"name": "Hà Đô", "industry": "Bất động sản / Năng lượng"},
    "POW": {"name": "PV Power", "industry": "Điện"},
    "NT2": {"name": "Điện Nhơn Trạch 2", "industry": "Điện"},
    "PPC": {"name": "Nhiệt điện Phả Lại", "industry": "Điện"},

    "VNM": {"name": "Vinamilk", "industry": "Thực phẩm"},
    "MSN": {"name": "Masan", "industry": "Tiêu dùng"},
    "SAB": {"name": "Sabeco", "industry": "Đồ uống"},
    "MCH": {"name": "Masan Consumer", "industry": "Tiêu dùng"},
    "QNS": {"name": "Đường Quảng Ngãi", "industry": "Thực phẩm"},
    "DBC": {"name": "Dabaco", "industry": "Nông nghiệp / Thực phẩm"},
    "BAF": {"name": "BAF Việt Nam", "industry": "Nông nghiệp / Thực phẩm"},

    "GMD": {"name": "Gemadept", "industry": "Cảng biển / Logistics"},
    "HAH": {"name": "Hải An", "industry": "Vận tải biển"},
    "VSC": {"name": "Viconship", "industry": "Cảng biển"},
    "VTP": {"name": "Viettel Post", "industry": "Logistics"},

    "DGC": {"name": "Hóa chất Đức Giang", "industry": "Hóa chất"},
    "CSV": {"name": "Hóa chất Cơ bản Miền Nam", "industry": "Hóa chất"},
    "DDV": {"name": "DAP Vinachem", "industry": "Hóa chất"},
    "DPM": {"name": "Đạm Phú Mỹ", "industry": "Phân bón"},
    "DCM": {"name": "Đạm Cà Mau", "industry": "Phân bón"},

    "VJC": {"name": "Vietjet Air", "industry": "Hàng không"},
    "HVN": {"name": "Vietnam Airlines", "industry": "Hàng không"},
    "ACV": {"name": "Cảng hàng không Việt Nam", "industry": "Hạ tầng hàng không"},
}


# =========================
# LOAD SYMBOLS
# =========================

def load_symbols():
    try:
        with open("symbols.txt", "r", encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        print("symbols.txt not found. Using fallback symbols.")
        raw = """
        VIC,VHM,VRE,FPT,HPG,HCM,SSI,VCI,VND,BID,CTG,MBB,
        TCB,ACB,STB,PVD,GEX,KBC,MWG,DGW,PNJ,DGC,GMD
        """

    symbols = []

    for line in raw.replace(",", "\n").splitlines():
        s = line.strip().upper()

        if not s:
            continue

        if s.startswith("#"):
            continue

        if s in BLACKLIST_SYMBOLS:
            continue

        symbols.append(s)

    unique_symbols = list(dict.fromkeys(symbols))
    print(f"Loaded {len(unique_symbols)} symbols after blacklist filter.")
    return unique_symbols


SYMBOLS = load_symbols()


# =========================
# HELPERS
# =========================

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
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
        df = df.dropna(subset=["time"])
        df = df.sort_values("time")

    return df.reset_index(drop=True)


# =========================
# FETCH DATA
# =========================

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

    # Loại mã không có nến mới
    if "time" in df.columns:
        latest_date = df["time"].iloc[-1]

        try:
            latest_date = latest_date.tz_localize(None)
        except Exception:
            pass

        stale_days = (pd.Timestamp.now().normalize() - latest_date.normalize()).days

        if stale_days > MAX_STALE_DAYS:
            raise ValueError(
                f"Inactive/stale symbol. Latest candle: {latest_date.date()}, stale {stale_days} days"
            )

    # Loại mã thanh khoản quá thấp
    avg_vol20 = df["volume"].tail(20).mean()
    recent_volume_days = (df["volume"].tail(20) > 0).sum()

    if avg_vol20 < MIN_AVG_VOL20:
        raise ValueError(f"Low liquidity. avgVol20={avg_vol20:.0f}")

    if recent_volume_days < MIN_RECENT_VOLUME_DAYS:
        raise ValueError(f"Too few recent trading days. recentVolumeDays={recent_volume_days}")

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


# =========================
# SCORING
# =========================

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

    # Trend score /20
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

    # Momentum score /15
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

    # Money score /20
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

    # Setup score /15
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

    # VIC Leap score /15
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

    # Risk score /10
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

    # T+ score /15
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

    is_bluechip = symbol in BLUECHIP_SYMBOLS

    is_penny = (
        price <= PENNY_MAX_PRICE and
        avg_vol20 >= PENNY_MIN_AVG_VOL20
    )

    categories = []

    if total_score >= 85:
        categories.append("Top cơ hội")
    if tplus >= 10:
        categories.append("Lướt sóng T+")
    if is_bluechip:
        categories.append("Bluechip")
    if is_penny:
        categories.append("Penny")
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

    if is_bluechip:
        positives.append("Thuộc nhóm Bluechip/vốn hóa lớn, thường có thanh khoản và độ quan tâm thị trường cao.")

    if is_penny:
        positives.append("Thuộc nhóm Penny có thanh khoản, phù hợp theo dõi sóng ngắn nhưng cần quản trị rủi ro chặt.")

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
    if is_penny:
        risks.append("Penny thường biến động mạnh, chỉ nên dùng tỷ trọng nhỏ và có điểm cắt lỗ rõ.")

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

    info = COMPANY_INFO.get(symbol, {})

    return {
        "symbol": symbol,
        "name": info.get("name", symbol),
        "industry": info.get("industry", "Chưa phân ngành"),

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


# =========================
# SAVE + MAIN
# =========================

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
