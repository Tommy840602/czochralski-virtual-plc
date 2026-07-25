"""訊號分類與相位定義。

逐點 parquet 有 70 欄，其中約 25 欄是每根晶棒固定不變的統計欄（*_COUNT、IS_* 等），
不屬於時序訊號，統一在此排除，避免前端選單被雜訊淹沒。
"""

# 時間軸與識別欄
TIME_COLUMN = "LogTime"
INGOT_COLUMN = "INGOT_NO"
MODE_COLUMN = "Operation Mode"

IDENTITY_COLUMNS = {
    INGOT_COLUMN,
    "DATASET_TYPE",
    "DATABASE_NAME",
    TIME_COLUMN,
    MODE_COLUMN,
    "SOP",
    "FIRST_FAILURE_PHASE",
}

# 每根晶棒為常數的統計欄位，非時序訊號
INGOT_LEVEL_SUFFIXES = ("_COUNT",)
INGOT_LEVEL_PREFIXES = ("IS_", "HAS_")

# 訊號分類：前端下拉選單依此分組
SIGNAL_GROUPS: dict[str, list[str]] = {
    "直徑 / 生長": [
        "Diameter",
        "D_mean",
        "Diameter target",
        "GR_mean",
        "Body length",
        "Neck Length Accum",
        "countb",
    ],
    "加熱 / 溫度": [
        "Heater Power SV",
        "Heater temp",
        "Heater temp target",
        "HTmean",
        "temp2",
        "temp4",
        "temp5",
        "temp9",
        "temp29",
    ],
    "晶種 / 坩堝": [
        "Seed lift",
        "Seed Lift SP",
        "Seed lift target",
        "Seed rotation SP",
        "Crucible Lift",
        "Crucible lift ratio",
        "Crucible position",
        "Crucible Position Calibrated",
        "Crucible rotation SP",
        "CRmean",
        "Residual Weight",
    ],
    "壓力 / 氣體": [
        "Argon gas flow rate",
        "Lower chamber press",
        "Lower chamber press SP",
        "Thro Valve Open",
        "BPmean",
        "BPU60mean",
        "BTPL_BPUL1",
        "BTPL_BPLL1",
    ],
    "PID / 磁場": [
        "PIDSL_temp1",
        "PIDSL_dDmean",
        "MAGNET PV",
        "CTPFL_PUL",
    ],
}

# 預設開啟的訊號組合：直徑控制迴路的三個主角
DEFAULT_SIGNALS = ["D_mean", "Heater Power SV", "Seed lift"]

# Operation Mode 歸併到四大相位，用於圖上色帶
PHASE_OF_MODE: dict[str, str] = {
    "NECK1": "NECK",
    "NECK2": "NECK",
    "NECK4": "NECK",
    "CROWN": "CROWN",
    "SHOULDER": "CROWN",
    "BODY": "BODY",
    "TAIL": "TAIL",
}

PHASE_ORDER = ["NECK", "CROWN", "BODY", "TAIL"]

GROUP_LABELS = {
    "g1": "單次 · 無異常",
    "g2": "單次 · 有異常",
    "g3": "多次 · 有異常",
    "g4": "多次 · 無異常",
}


def is_ingot_level(column: str) -> bool:
    return column.endswith(INGOT_LEVEL_SUFFIXES) or column.startswith(INGOT_LEVEL_PREFIXES)


def classify(columns: list[str]) -> list[dict]:
    """把 parquet 欄位切成前端要的 [{group, signals:[...]}]，未分類者歸「其他」。"""
    known = {name for names in SIGNAL_GROUPS.values() for name in names}
    available = {
        c for c in columns if c not in IDENTITY_COLUMNS and not is_ingot_level(c)
    }

    result = []
    for group, names in SIGNAL_GROUPS.items():
        present = [n for n in names if n in available]
        if present:
            result.append({"group": group, "signals": present})

    others = sorted(available - known)
    if others:
        result.append({"group": "其他", "signals": others})
    return result
