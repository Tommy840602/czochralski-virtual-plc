from functools import lru_cache
import posixpath
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> backend/app -> backend -> plc-research -> output
_DEFAULT_DATA_ROOT = str(Path(__file__).resolve().parents[3].parent)


class Settings(BaseSettings):
    """所有路徑集中在此，之後換資料來源（DB / 物件儲存）只需改這裡與 repository。"""

    model_config = SettingsConfigDict(env_prefix="PLC_", env_file=".env")

    # 本機絕對路徑或 GCS URI，例如 gs://my-bucket/plc-data
    data_root: str = _DEFAULT_DATA_ROOT
    # 留空時 gcsfs 會使用 Application Default Credentials / Workload Identity。
    gcs_project: str | None = None
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # 登入（本機單人研究用；正式部署請以環境變數覆寫）
    auth_username: str = "admin"
    auth_password: str = "admin0000"
    auth_secret: str = "dev-secret-change-me-please-use-32+chars"
    token_ttl_hours: int = 12

    # 單一訊號回傳前端的最大點數，超過則以 LTTB 降採樣
    max_series_points: int = 3000
    # 讀進記憶體的晶棒逐點資料快取數量（每根約 11k 列 × 70 欄）
    ingot_cache_size: int = 24

    @property
    def storage_scheme(self) -> str:
        return "gcs" if self.data_root.startswith("gs://") else "local"

    def data_path(self, *parts: str) -> str:
        """在本機路徑與 gs:// URI 間使用一致的 POSIX key 組合。"""
        root = self.data_root.rstrip("/")
        return posixpath.join(root, *parts)

    @property
    def rawdata_dir(self) -> str:
        return self.data_path("rawdata")

    @property
    def table2_dir(self) -> str:
        return self.data_path("table2")

    @property
    def segment_summary_path(self) -> str:
        return self.data_path("segment_summary.parquet")

    @property
    def precursor_windows_path(self) -> str:
        return self.data_path("precursor_windows.csv")

    @property
    def precursor_auc_path(self) -> str:
        return self.data_path("precursor_auc.csv")

    @property
    def precursor_sweep_path(self) -> str:
        return self.data_path("precursor_sweep.csv")

    @property
    def profile_band_path(self) -> str:
        return self.data_path("profile_band.csv")

    @property
    def profile_scores_path(self) -> str:
        return self.data_path("profile_scores.csv")

    @property
    def group_csv_paths(self) -> dict[str, str]:
        return {
            "g1": self.data_path("G1_single_no_fault.csv"),
            "g2": self.data_path("G2_single_with_fault.csv"),
            "g3": self.data_path("G3_multi_with_fault.csv"),
            "g4": self.data_path("G4_multi_no_fault.csv"),
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
