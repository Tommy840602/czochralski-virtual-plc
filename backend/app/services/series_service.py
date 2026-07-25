import numpy as np
import pandas as pd

from app.core.config import Settings
from app.core.signals import MODE_COLUMN, PHASE_OF_MODE, TIME_COLUMN
from app.repositories.base import DataRepository
from app.services.catalog_service import records
from app.services.downsample import downsample_frame


class SeriesService:
    def __init__(self, repo: DataRepository, settings: Settings):
        self.repo = repo
        self.settings = settings

    def series(
        self,
        ingot_no: str,
        signals: list[str],
        start: pd.Timestamp | None = None,
        end: pd.Timestamp | None = None,
        segment_seq: int | None = None,
        max_points: int | None = None,
    ) -> dict:
        df = self.repo.load_series(ingot_no)
        segments = self.repo.load_segments()
        seg = segments[segments["INGOT_NO"] == ingot_no].sort_values("SEGMENT_SEQ")

        # 指定段落時，以該段的起訖時間覆寫視窗
        if segment_seq is not None:
            match = seg[seg["SEGMENT_SEQ"] == segment_seq]
            if not match.empty:
                start = match.iloc[0]["START_TIME"]
                end = match.iloc[0]["END_TIME"]

        window = df
        if start is not None:
            window = window[window[TIME_COLUMN] >= start]
        if end is not None:
            window = window[window[TIME_COLUMN] <= end]

        missing = [s for s in signals if s not in df.columns]
        available = [s for s in signals if s in df.columns]
        threshold = max_points or self.settings.max_series_points

        ts = window[TIME_COLUMN].to_numpy("datetime64[ms]").astype(np.int64)
        out_series = []
        for name in available:
            values = pd.to_numeric(window[name], errors="coerce").to_numpy(float)
            keep = downsample_frame(ts, values, threshold)
            points = [[int(t), float(v)] for t, v in zip(ts[keep], values[keep])]
            finite = values[~np.isnan(values)]
            out_series.append(
                {
                    "name": name,
                    "points": points,
                    "stats": {
                        "min": float(finite.min()) if finite.size else None,
                        "max": float(finite.max()) if finite.size else None,
                        "mean": float(finite.mean()) if finite.size else None,
                        "count": int(finite.size),
                    },
                }
            )

        return {
            "ingotNo": ingot_no,
            "totalPoints": int(len(window)),
            "maxPoints": threshold,
            "missingSignals": missing,
            "series": out_series,
            "modes": self._mode_spans(window),
            "segments": self._segment_spans(seg, start, end),
        }

    def _mode_spans(self, window: pd.DataFrame) -> list[dict]:
        """把 Operation Mode 的連續區段壓成色帶，供圖上標註製程階段。"""
        if window.empty or MODE_COLUMN not in window.columns:
            return []

        modes = window[MODE_COLUMN].astype("string").fillna("UNKNOWN")
        times = window[TIME_COLUMN].to_numpy("datetime64[ms]").astype(np.int64)
        # 值變動處即為區段邊界
        change = np.flatnonzero(modes.to_numpy()[1:] != modes.to_numpy()[:-1]) + 1
        bounds = np.concatenate([[0], change, [len(modes)]])

        spans = []
        for lo, hi in zip(bounds[:-1], bounds[1:]):
            mode = str(modes.iloc[lo])
            spans.append(
                {
                    "mode": mode,
                    "phase": PHASE_OF_MODE.get(mode),
                    "start": int(times[lo]),
                    "end": int(times[hi - 1]),
                }
            )
        return spans

    def _segment_spans(
        self, seg: pd.DataFrame, start, end
    ) -> list[dict]:
        if seg.empty:
            return []
        rows = seg
        if start is not None:
            rows = rows[rows["END_TIME"] >= start]
        if end is not None:
            rows = rows[rows["START_TIME"] <= end]

        out = []
        for _, r in rows.iterrows():
            out.append(
                {
                    "segmentSeq": int(r["SEGMENT_SEQ"]),
                    "passSeq": int(r["PASS_SEQ"]),
                    "phase": r["PHASE"],
                    "start": int(pd.Timestamp(r["START_TIME"]).value // 1_000_000),
                    "end": int(pd.Timestamp(r["END_TIME"]).value // 1_000_000),
                    "durationMin": float(r["DURATION_MIN"]),
                    "endedBy": r["ENDED_BY"],
                    "faultCount": int(r["FAULT_COUNT"]),
                    "isClean": bool(r["IS_CLEAN"]),
                }
            )
        return out

    def compare(
        self, ingot_nos: list[str], signal: str, normalize: bool = True
    ) -> dict:
        """多根晶棒疊圖。時間軸改用相對進度，否則不同開爐時間無法對齊。"""
        threshold = self.settings.max_series_points
        out = []
        for ingot_no in ingot_nos:
            try:
                df = self.repo.load_series(ingot_no)
            except KeyError:
                continue
            if signal not in df.columns:
                continue

            values = pd.to_numeric(df[signal], errors="coerce").to_numpy(float)
            times = df[TIME_COLUMN].to_numpy("datetime64[ms]").astype(np.int64)
            keep = downsample_frame(times, values, threshold)
            if keep.size == 0:
                continue

            kept_times = times[keep]
            if normalize:
                span = kept_times[-1] - kept_times[0]
                axis = (
                    (kept_times - kept_times[0]) / span
                    if span > 0
                    else np.zeros_like(kept_times, dtype=float)
                )
            else:
                axis = (kept_times - kept_times[0]) / 3_600_000  # 小時

            out.append(
                {
                    "ingotNo": ingot_no,
                    "points": [
                        [float(a), float(v)] for a, v in zip(axis, values[keep])
                    ],
                }
            )

        return {
            "signal": signal,
            "xLabel": "製程進度 (0–1)" if normalize else "自開始時數 (h)",
            "series": out,
        }
