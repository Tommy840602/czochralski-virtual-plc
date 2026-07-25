import math

import numpy as np
import pandas as pd

from app.core.signals import GROUP_LABELS, classify
from app.repositories.base import DataRepository

# 目錄列表回傳的欄位，其餘統計欄留在詳情頁
LIST_COLUMNS = [
    "INGOT_NO",
    "GROUP",
    "DATABASE_NAME",
    "CREATETIME",
    "HAS_GENERAL_FAULT",
    "IS_SINGLE_PASS",
    "IS_MULTI_PASS",
    "ATTEMPT_COUNT",
    "GENERAL_FAULT_COUNT",
    "PROCESS_FAULT_COUNT",
    "EQUIPMENT_FAULT_COUNT",
    "TOTAL_EVENT_COUNT",
]

FAULT_BREAKDOWN = [
    ("NECK_TRIP_COUNT", "縮頸斷線"),
    ("CROWN_BREAK_COUNT", "放肩斷線"),
    ("SHOULDER_BREAK_COUNT", "轉肩斷線"),
    ("BODY_BREAK_COUNT", "等徑斷線"),
    ("TAIL_BREAK_COUNT", "收尾斷線"),
    ("EARTHQUAKE_BREAK_COUNT", "地震斷線"),
]


def _clean(value):
    """把 numpy / NaT / NaN 轉成 JSON 安全的值。"""
    if value is None or value is pd.NaT:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if math.isnan(value) else float(value)
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def records(df: pd.DataFrame) -> list[dict]:
    return [{k: _clean(v) for k, v in row.items()} for row in df.to_dict("records")]


class CatalogService:
    def __init__(self, repo: DataRepository):
        self.repo = repo

    def signal_meta(self) -> dict:
        return {
            "signalGroups": classify(self.repo.series_columns()),
            "groups": [
                {"value": key, "label": f"{key.upper()} · {label}"}
                for key, label in GROUP_LABELS.items()
            ],
        }

    def summary(self) -> dict:
        """首頁的整體統計：分組計數、異常率、爐台分布。"""
        catalog = self.repo.list_ingots()
        segments = self.repo.load_segments()

        by_group = (
            catalog.groupby("GROUP")
            .agg(
                ingots=("INGOT_NO", "count"),
                faults=("HAS_GENERAL_FAULT", "sum"),
            )
            .reset_index()
        )
        by_group["label"] = by_group["GROUP"].map(GROUP_LABELS)

        by_furnace = (
            catalog.groupby("DATABASE_NAME")
            .agg(ingots=("INGOT_NO", "count"), faults=("HAS_GENERAL_FAULT", "sum"))
            .reset_index()
            .sort_values("ingots", ascending=False)
        )

        phase_breaks = (
            segments[segments["ENDED_BY"] == "BREAK"]["PHASE"]
            .value_counts()
            .rename_axis("phase")
            .reset_index(name="breaks")
        )

        return {
            "totalIngots": int(len(catalog)),
            "faultIngots": int(catalog["HAS_GENERAL_FAULT"].sum()),
            "totalSegments": int(len(segments)),
            "breakSegments": int((segments["ENDED_BY"] == "BREAK").sum()),
            "byGroup": records(by_group),
            "byFurnace": records(by_furnace),
            "breaksByPhase": records(phase_breaks),
        }

    def list_ingots(
        self,
        groups: list[str] | None = None,
        furnaces: list[str] | None = None,
        has_fault: bool | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> dict:
        df = self.repo.list_ingots()

        if groups:
            df = df[df["GROUP"].isin(groups)]
        if furnaces:
            df = df[df["DATABASE_NAME"].isin(furnaces)]
        if has_fault is not None:
            df = df[df["HAS_GENERAL_FAULT"].astype(bool) == has_fault]
        if keyword:
            df = df[df["INGOT_NO"].str.contains(keyword.strip(), case=False, na=False)]

        total = len(df)
        start = (page - 1) * page_size
        page_df = df.iloc[start : start + page_size]
        columns = [c for c in LIST_COLUMNS if c in page_df.columns]

        return {
            "total": total,
            "page": page,
            "pageSize": page_size,
            "items": records(page_df[columns]),
        }

    def facets(self) -> dict:
        df = self.repo.list_ingots()
        return {
            "furnaces": sorted(df["DATABASE_NAME"].dropna().unique().tolist()),
            "groups": [
                {"value": g, "label": GROUP_LABELS.get(g, g)}
                for g in sorted(df["GROUP"].unique())
            ],
        }

    def ingot_detail(self, ingot_no: str) -> dict:
        catalog = self.repo.list_ingots()
        row = catalog[catalog["INGOT_NO"] == ingot_no]
        if row.empty:
            raise KeyError(ingot_no)
        meta = records(row)[0]

        segments = self.repo.load_segments()
        seg = segments[segments["INGOT_NO"] == ingot_no].sort_values("SEGMENT_SEQ")

        breakdown = [
            {"key": key, "label": label, "count": int(meta.get(key) or 0)}
            for key, label in FAULT_BREAKDOWN
            if (meta.get(key) or 0) > 0
        ]

        return {
            "meta": meta,
            "groupLabel": GROUP_LABELS.get(meta.get("GROUP"), ""),
            "faultBreakdown": breakdown,
            "segments": records(seg),
        }

    def ingot_events(self, ingot_no: str) -> list[dict]:
        events = self.repo.load_events(ingot_no)
        if events.empty:
            return []
        cols = [
            "RECORDTIME",
            "OPERATE_ITEM_ID",
            "OPERATE_ITEM_NAME_CH",
            "Message",
            "Label",
        ]
        return records(events[[c for c in cols if c in events.columns]])
