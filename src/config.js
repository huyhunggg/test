export const API_KEY = process.env.VNSTOCK_API_KEY;

export const BASE_URL =
  process.env.VNSTOCK_BASE_URL || "https://api.vnstock.vn";

export const OHLCV_URL =
  process.env.VNSTOCK_OHLCV_URL || "";

export const SYMBOLS = (
  process.env.SYMBOLS ||
  [
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
  ].join(",")
)
  .split(",")
  .map(x => x.trim())
  .filter(Boolean);

export const COMPANY_INFO = {
  VIC: { name: "Tập đoàn Vingroup", industry: "Bất động sản / Holding" },
  VHM: { name: "Vinhomes", industry: "Bất động sản" },
  VRE: { name: "Vincom Retail", industry: "Bất động sản bán lẻ" },

  FPT: { name: "FPT Corporation", industry: "Công nghệ" },
  FOX: { name: "FPT Telecom", industry: "Công nghệ / Viễn thông" },
  CMG: { name: "CMC Corp", industry: "Công nghệ" },
  ELC: { name: "ELCOM", industry: "Công nghệ" },

  MWG: { name: "Thế Giới Di Động", industry: "Bán lẻ" },
  DGW: { name: "Digiworld", industry: "Bán lẻ / Phân phối" },

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
  DDV: { name: "DAP Vinachem", industry: "Hóa chất" }
};
