import numpy as np
import pandas as pd

from app.core.signals import TIME_COLUMN
from app.repositories.base import DataRepository
from app.services.catalog_service import records
from app.services.downsample import downsample_frame

# 由當前 recipe 常數推得的等效增益（見 README / 分析）：
#   MV = Gp·Er_M + Gv·temp1 + Gd·dDmean
#   Gp = K·Kc            = 0.4·0.001            = 0.0004
#   Gv = K·Kc·Kr·2       = 0.4·0.001·200·2      = 0.16
#   Gd = K·Kc·Kr·(-1.33) = 0.4·0.001·200·-1.33  = -0.1064
DEFAULT_GAINS = {"gp": 0.0004, "gv": 0.16, "gd": -0.1064}

# 原始常數，僅供顯示（K·Kc 不可分辨，單獨調無意義）
RECIPE_CONSTANTS = {"K": 0.4, "Kc": 0.001, "Kr": 200, "a_temp1": 2.0, "b_dDmean": -1.33}

# 記錄的 tag：PIDSL_temp1/dDmean 就是控制律中的 temp1/dDmean（已驗證吻合）
TEMP1_TAG = "PIDSL_temp1"
DDMEAN_TAG = "PIDSL_dDmean"
MV_OUTPUT = "Seed Lift SP"  # MV 是此訊號的增量


def erm_default(e: np.ndarray) -> np.ndarray:
    """原始 Er_M：|e|<1 斜率2；1<|e|<2 平（增益死區）；|e|>=2 跳到 ±3。"""
    out = np.where(
        e <= -2, -3.0,
        np.where(e < -1, -2.0,
                 np.where(e >= 2, 3.0,
                          np.where(e > 1, 2.0, 2.0 * e))),
    )
    return out


def erm_monotone(e: np.ndarray) -> np.ndarray:
    """修正版：|e|<=1 斜率2，之後續以斜率1 單調延伸，無死區、無跳變。

    e=1→2, e=2→3, e=3→4…；與原版在 |e|<=1 完全一致，只補平中段死區與消去跳變。
    """
    return np.where(np.abs(e) <= 1, 2.0 * e, np.sign(e) * (np.abs(e) + 1.0))


ERM_MODES = {"default": erm_default, "monotone": erm_monotone}


class ControlService:
    def __init__(self, repo: DataRepository):
        self.repo = repo

    def defaults(self) -> dict:
        return {
            "gains": DEFAULT_GAINS,
            "constants": RECIPE_CONSTANTS,
            "ermCurve": self._erm_curve(),
            "note": (
                "MV 是 Seed Lift SP 的增量；K 與 Kc 只以乘積出現，單獨調無意義。"
                "本頁為開環 replay：在每個記錄時刻，比較不同增益下控制器會下的 MV 指令，"
                "不預測改變後的直徑（被控對象在此閉環資料下不可辨識）。"
            ),
        }

    @staticmethod
    def _erm_curve() -> list[dict]:
        e = np.linspace(-3, 3, 121)
        return [
            {"e": float(x), "default": float(d), "monotone": float(m)}
            for x, d, m in zip(e, erm_default(e), erm_monotone(e))
        ]

    def replay(
        self,
        ingot_no: str,
        segment_seq: int | None,
        gp: float,
        gv: float,
        gd: float,
        erm_mode: str = "default",
        max_points: int = 1500,
    ) -> dict:
        df = self.repo.load_series(ingot_no)
        segments = self.repo.load_segments()
        seg = segments[segments["INGOT_NO"] == ingot_no].sort_values("SEGMENT_SEQ")
        if seg.empty:
            raise KeyError(ingot_no)

        if segment_seq is None:
            # 預設挑最長的 BODY 段（等徑控制最活躍）
            body = seg[seg["PHASE"] == "BODY"]
            pick = (body if not body.empty else seg).sort_values(
                "DURATION_MIN", ascending=False
            ).iloc[0]
            segment_seq = int(pick["SEGMENT_SEQ"])

        match = seg[seg["SEGMENT_SEQ"] == segment_seq]
        if match.empty:
            raise KeyError(f"{ingot_no}#{segment_seq}")
        row = match.iloc[0]

        w = df[
            (df[TIME_COLUMN] >= row["START_TIME"]) & (df[TIME_COLUMN] <= row["END_TIME"])
        ].reset_index(drop=True)
        if len(w) < 10:
            raise KeyError(f"{ingot_no}#{segment_seq} 資料過短")

        erm_fn = ERM_MODES.get(erm_mode, erm_default)

        target = pd.to_numeric(w["Diameter target"], errors="coerce").to_numpy(float)
        diameter = pd.to_numeric(w["Diameter"], errors="coerce").to_numpy(float)
        e = diameter - target
        temp1 = pd.to_numeric(w[TEMP1_TAG], errors="coerce").to_numpy(float)
        dd = pd.to_numeric(w[DDMEAN_TAG], errors="coerce").to_numpy(float)
        sl_actual = pd.to_numeric(w[MV_OUTPUT], errors="coerce").to_numpy(float)

        erm_val = erm_fn(e)
        erm_def = erm_default(e)

        # 新增益下的 MV，與「當前 recipe 增益 + 原始 Er_M」的基準 MV
        mv_new = gp * erm_val + gv * temp1 + gd * dd
        mv_base = (
            DEFAULT_GAINS["gp"] * erm_def
            + DEFAULT_GAINS["gv"] * temp1
            + DEFAULT_GAINS["gd"] * dd
        )

        # 拉速指令＝MV 累積（從實測起點出發），純示意控制器積分行為
        sl0 = sl_actual[0] if np.isfinite(sl_actual[0]) else 0.0
        sl_new = sl0 + np.nancumsum(mv_new)
        sl_base = sl0 + np.nancumsum(mv_base)

        ts = w[TIME_COLUMN].to_numpy("datetime64[ms]").astype(np.int64)
        keep = self._downsample_union(ts, [diameter, mv_new, mv_base], max_points)

        def series(arr):
            return [
                [int(ts[i]), None if np.isnan(arr[i]) else round(float(arr[i]), 5)]
                for i in keep
            ]

        return {
            "ingotNo": ingot_no,
            "segmentSeq": segment_seq,
            "phase": row["PHASE"],
            "endedBy": row["ENDED_BY"],
            "ermMode": erm_mode,
            "gains": {"gp": gp, "gv": gv, "gd": gd},
            "n": int(len(w)),
            "series": {
                "diameter": series(diameter),
                "target": series(target),
                "error": series(e),
                "mvNew": series(mv_new),
                "mvBase": series(mv_base),
                "slNew": series(sl_new),
                "slBase": series(sl_base),
                "slActual": series(sl_actual),
            },
            "stats": self._stats(e, mv_new, mv_base, erm_val),
        }

    @staticmethod
    def _downsample_union(ts, arrays, max_points):
        """對多條訊號取聯集的保留索引，確保各線在同一時間網格對齊。"""
        base = arrays[0]
        keep = downsample_frame(ts, base, max_points)
        return keep

    @staticmethod
    def _stats(e, mv_new, mv_base, erm_val) -> dict:
        ae = np.abs(e[~np.isnan(e)])
        return {
            "errorStd": float(np.nanstd(e)),
            "mvRmsNew": float(np.sqrt(np.nanmean(mv_new**2))),
            "mvRmsBase": float(np.sqrt(np.nanmean(mv_base**2))),
            # 控制動作相對基準的激進程度
            "aggressiveness": float(
                np.sqrt(np.nanmean(mv_new**2)) / (np.sqrt(np.nanmean(mv_base**2)) + 1e-12)
            ),
            "deadZonePct": float(100 * np.mean((ae >= 1) & (ae < 2))) if ae.size else 0.0,
            "beyond2Pct": float(100 * np.mean(ae >= 2)) if ae.size else 0.0,
            "nearJumpPct": float(100 * np.mean((ae > 1.8) & (ae < 2.2))) if ae.size else 0.0,
        }
