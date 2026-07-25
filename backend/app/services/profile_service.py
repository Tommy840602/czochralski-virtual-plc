import numpy as np
import pandas as pd

from app.core.signals import TIME_COLUMN
from app.repositories.base import DataRepository
from app.services.catalog_service import records

# 包絡帶所描述的訊號：離線 pipeline 以此建立正常製程的參考輪廓
PROFILE_SIGNAL = "Heater Power SV"
POSITION_SIGNAL = "Body length"

# 管制圖指標與對應的越界旗標
CONTROL_METRICS = [
    ("T2", "T2_EXCEED", "T² 統計量", "主成分空間內的偏離程度"),
    ("SPE", "SPE_EXCEED", "SPE (Q)", "無法被主成分解釋的殘差"),
    ("LEVEL_RESID", "LEVEL_EXCEED", "LEVEL 殘差", "功率水平相對同型晶棒的偏移"),
]


class ProfileService:
    def __init__(self, repo: DataRepository):
        self.repo = repo

    def band(self) -> dict:
        df = self.repo.load_profile_band()
        return {
            "signal": PROFILE_SIGNAL,
            "positionLabel": "等徑段長度進度 (0–1)",
            "points": [
                {
                    "u": float(r.u),
                    "mean": float(r["mean"]),
                    "lo": float(r.lo),
                    "hi": float(r.hi),
                }
                for _, r in df.iterrows()
            ],
        }

    def control_limits(self) -> dict:
        """由 EXCEED 旗標反推離線 pipeline 使用的管制界線。

        原始資料只留旗標沒留門檻，取「未越界最大值」與「越界最小值」的中點，
        誤差不超過兩者間距，畫在圖上足夠精確。
        """
        scores = self.repo.load_profile_scores()
        limits = {}
        for metric, flag, label, desc in CONTROL_METRICS:
            below = scores.loc[scores[flag] == 0, metric]
            above = scores.loc[scores[flag] == 1, metric]
            if above.empty:
                limit = float(below.quantile(0.99)) if not below.empty else None
            else:
                limit = float((below.max() + above.min()) / 2)
            limits[metric] = {
                "label": label,
                "description": desc,
                "limit": limit,
                "exceedCount": int(scores[flag].sum()),
            }
        return limits

    def scores(
        self,
        only_ooc: bool = False,
        ended_by: list[str] | None = None,
        clean: bool | None = None,
    ) -> dict:
        df = self.repo.load_profile_scores()
        if only_ooc:
            df = df[df["OOC"] == 1]
        if ended_by:
            df = df[df["ENDED_BY"].isin(ended_by)]
        if clean is not None:
            df = df[df["IS_CLEAN"] == int(clean)]

        limits = self.control_limits()
        oc = self.repo.load_profile_scores()

        return {
            "limits": limits,
            "total": int(len(oc)),
            "oocTotal": int(oc["OOC"].sum()),
            "endedByOptions": sorted(oc["ENDED_BY"].dropna().unique().tolist()),
            "items": records(df.sort_values("T2", ascending=False)),
        }

    def confusion(self) -> dict:
        """OOC 告警與實際斷線（ENDED_BY=BREAK）的交叉表，用來看監控有沒有用。"""
        df = self.repo.load_profile_scores()
        broke = df["ENDED_BY"] == "BREAK"
        ooc = df["OOC"] == 1
        tp, fp = int((ooc & broke).sum()), int((ooc & ~broke).sum())
        fn, tn = int((~ooc & broke).sum()), int((~ooc & ~broke).sum())
        return {
            "truePositive": tp,
            "falsePositive": fp,
            "falseNegative": fn,
            "trueNegative": tn,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
            "breakRate": float(broke.mean()),
        }

    def ingot_profile(self, ingot_no: str, segment_seq: int | None = None) -> dict:
        """把指定段落的實際輪廓重採樣到包絡帶的 u 網格，供前端疊圖。"""
        scores = self.repo.load_profile_scores()
        rows = scores[scores["INGOT_NO"] == ingot_no]
        if rows.empty:
            raise KeyError(ingot_no)

        if segment_seq is None:
            segment_seq = int(rows.iloc[0]["SEGMENT_SEQ"])
        row = rows[rows["SEGMENT_SEQ"] == segment_seq]
        if row.empty:
            raise KeyError(f"{ingot_no}#{segment_seq}")
        score = records(row)[0]

        segments = self.repo.load_segments()
        seg = segments[
            (segments["INGOT_NO"] == ingot_no)
            & (segments["SEGMENT_SEQ"] == segment_seq)
        ]
        if seg.empty:
            raise KeyError(f"{ingot_no}#{segment_seq}")
        seg = seg.iloc[0]

        df = self.repo.load_series(ingot_no)
        window = df[
            (df[TIME_COLUMN] >= seg["START_TIME"]) & (df[TIME_COLUMN] <= seg["END_TIME"])
        ]

        band = self.repo.load_profile_band()
        grid = band["u"].to_numpy(float)
        y = pd.to_numeric(window[PROFILE_SIGNAL], errors="coerce").to_numpy(float)
        u = self._position_axis(window, y)

        valid = ~np.isnan(y)
        if valid.sum() < 2:
            profile = np.full_like(grid, np.nan)
        else:
            order = np.argsort(u[valid])
            profile = np.interp(grid, u[valid][order], y[valid][order])

        lo, hi = band["lo"].to_numpy(float), band["hi"].to_numpy(float)
        outside = (profile < lo) | (profile > hi)

        return {
            "ingotNo": ingot_no,
            "segmentSeq": segment_seq,
            "phase": seg["PHASE"],
            "endedBy": seg["ENDED_BY"],
            "signal": PROFILE_SIGNAL,
            "score": score,
            "limits": self.control_limits(),
            "availableSegments": records(
                rows[["SEGMENT_SEQ", "PASS_SEQ", "T2", "SPE", "OOC", "ENDED_BY"]]
            ),
            "band": [
                {"u": float(a), "mean": float(m), "lo": float(l), "hi": float(h)}
                for a, m, l, h in zip(grid, band["mean"], lo, hi)
            ],
            "profile": [
                {"u": float(a), "value": None if np.isnan(v) else float(v)}
                for a, v in zip(grid, profile)
            ],
            "outsideRatio": float(outside[~np.isnan(profile)].mean())
            if (~np.isnan(profile)).any()
            else None,
        }

    @staticmethod
    def _position_axis(window: pd.DataFrame, y: np.ndarray) -> np.ndarray:
        """優先用晶棒長度當橫軸；長度沒有進展時（如 NECK 段）退回時間比例。"""
        if POSITION_SIGNAL in window.columns:
            pos = pd.to_numeric(window[POSITION_SIGNAL], errors="coerce").to_numpy(float)
            span = np.nanmax(pos) - np.nanmin(pos) if np.isfinite(pos).any() else 0
            if span > 1e-6:
                return (pos - np.nanmin(pos)) / span
        return np.linspace(0, 1, len(y))
