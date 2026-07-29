from functools import lru_cache
import posixpath
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> backend/app -> backend -> cz-virtual-plc -> output
_DEFAULT_DATA_ROOT = str(Path(__file__).resolve().parents[3].parent)
DEFAULT_AUTH_USERNAME = "admin"
DEFAULT_AUTH_PASSWORD = "admin0000"
DEFAULT_AUTH_SECRET = "dev-secret-change-me-please-use-32+chars"


class Settings(BaseSettings):
    """所有路徑集中在此，之後換資料來源（DB / 物件儲存）只需改這裡與 repository。"""

    model_config = SettingsConfigDict(env_prefix="PLC_", env_file=".env")

    environment: Literal["development", "test", "production"] = "development"

    # 本機絕對路徑或 GCS URI，例如 gs://my-bucket/plc-data
    data_root: str = _DEFAULT_DATA_ROOT
    # 留空時 gcsfs 會使用 Application Default Credentials / Workload Identity。
    gcs_project: str | None = None
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # 展示環境 RBAC：三個角色共用受保護密碼，身份與權限寫入簽章 token。
    auth_username: str = DEFAULT_AUTH_USERNAME
    auth_engineer_username: str = "plc.engineer"
    auth_lead_username: str = "plc.lead"
    auth_password: str = DEFAULT_AUTH_PASSWORD
    auth_secret: str = DEFAULT_AUTH_SECRET
    token_ttl_hours: int = 12
    database_url: str = "postgresql://plc:plc@127.0.0.1:5434/plc"
    database_schema: str = "plc_identity"

    # 單一訊號回傳前端的最大點數，超過則以 LTTB 降採樣
    max_series_points: int = 3000
    # 讀進記憶體的晶棒逐點資料快取數量（每根約 11k 列 × 70 欄）
    ingot_cache_size: int = 24

    # Virtual PLC runtime；開發環境預設關閉，接上 Plant Simulator 時再啟用。
    runtime_enabled: bool = False
    scan_interval_seconds: float = Field(default=0.2, gt=0.0, le=5.0)
    plant_opcua_endpoint: str = (
        "opc.tcp://plant-simulator:4840/plant-simulator/server/"
    )
    plant_opcua_namespace: str = "urn:tommy-huang:cz-plant-simulator"
    plant_api_url: str = "http://plant-simulator:8090"

    @model_validator(mode="after")
    def _validate_production_security(self):
        if self.environment != "production":
            return self
        errors = []
        if not self.database_url.startswith("postgresql://"):
            errors.append("PLC_DATABASE_URL 必須使用 PostgreSQL")
        if self.auth_username == DEFAULT_AUTH_USERNAME:
            errors.append("PLC_AUTH_USERNAME 不得使用預設 admin")
        identities = {
            self.auth_username,
            self.auth_engineer_username,
            self.auth_lead_username,
        }
        if len(identities) != 3 or any(not item.strip() for item in identities):
            errors.append("Operator、Engineer、Lead 登入帳號必須非空且不可重複")
        if self.auth_password == DEFAULT_AUTH_PASSWORD or len(self.auth_password) < 12:
            errors.append("PLC_AUTH_PASSWORD 必須是至少 12 字元的非預設密碼")
        if self.auth_secret == DEFAULT_AUTH_SECRET or len(self.auth_secret) < 32:
            errors.append("PLC_AUTH_SECRET 必須是至少 32 字元的非預設隨機值")
        if "*" in self.cors_origins:
            errors.append("PLC_CORS_ORIGINS 不得包含萬用來源 *")
        if errors:
            raise ValueError("production 安全設定不完整：" + "；".join(errors))
        return self

    @property
    def auth_identities(self) -> dict[str, str]:
        return {
            self.auth_username: "Operator",
            self.auth_engineer_username: "Engineer",
            self.auth_lead_username: "Lead",
        }

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
