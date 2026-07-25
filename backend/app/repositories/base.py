from abc import ABC, abstractmethod

import pandas as pd


class DataRepository(ABC):
    """資料存取契約。

    ParquetRepository 已支援本機與 GCS；日後要換成 DuckDB / Postgres，實作這個
    介面即可，service 與 API 層不動。
    """

    @abstractmethod
    def list_ingots(self) -> pd.DataFrame:
        """每根晶棒一列的目錄表，含分組與事件統計欄。"""

    @abstractmethod
    def load_series(self, ingot_no: str) -> pd.DataFrame:
        """單根晶棒的逐點 PLC 訊號，依 LogTime 排序。"""

    @abstractmethod
    def load_events(self, ingot_no: str) -> pd.DataFrame:
        """單根晶棒的事件記錄（table2）。"""

    @abstractmethod
    def load_segments(self) -> pd.DataFrame:
        """全體晶棒的相位切段摘要。"""

    @abstractmethod
    def load_precursor_windows(self) -> pd.DataFrame:
        """前兆分析的視窗特徵矩陣，含 case/control 標籤。"""

    @abstractmethod
    def load_precursor_auc(self) -> pd.DataFrame:
        """離線算好的 AUC 排行。"""

    @abstractmethod
    def load_precursor_sweep(self) -> pd.DataFrame:
        """AUC 對前置時間 offset 的掃描結果。"""

    @abstractmethod
    def load_profile_band(self) -> pd.DataFrame:
        """正常製程的 profile 包絡帶。"""

    @abstractmethod
    def load_profile_scores(self) -> pd.DataFrame:
        """各段的 T2 / SPE / LEVEL 偏離分數。"""
