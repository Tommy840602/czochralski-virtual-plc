import functools
from pathlib import PurePosixPath
import threading

import fsspec
import pandas as pd

from app.core.config import Settings
from app.core.signals import TIME_COLUMN
from app.repositories.base import DataRepository

_CSV_KW = {"encoding": "utf-8-sig"}


class ParquetRepository(DataRepository):
    """透過 fsspec 讀本機或 GCS 上的 parquet / csv。

    小表（segment_summary、precursor、profile）在第一次存取時整份載入並常駐，
    合計不到 100MB；逐點資料則以 LRU 快取住最近讀過的幾根晶棒。
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        storage_options = {}
        if settings.storage_scheme == "gcs" and settings.gcs_project:
            storage_options["project"] = settings.gcs_project
        # url_to_fs 會移除 gs:// protocol；之後所有操作都交給同一個 filesystem。
        self.fs, self._root = fsspec.core.url_to_fs(
            settings.data_root, **storage_options
        )
        self._root = self._root.rstrip("/")
        self._lock = threading.Lock()
        self._small_tables: dict[str, pd.DataFrame] = {}
        self._series_cache = functools.lru_cache(maxsize=settings.ingot_cache_size)(
            self._read_series
        )

    # ---------- 內部工具 ----------

    def _storage_path(self, uri: str) -> str:
        """把設定中的完整 URI 轉為目前 filesystem 使用的內部路徑。"""
        return self.fs._strip_protocol(uri)

    def _read_csv(self, uri: str) -> pd.DataFrame:
        with self.fs.open(self._storage_path(uri), "rb") as stream:
            return pd.read_csv(stream, **_CSV_KW)

    def _read_parquet(self, uri: str, **kwargs) -> pd.DataFrame:
        # gcsfs file object 支援 seek/range request，PyArrow 不必先下載整個 bucket。
        with self.fs.open(self._storage_path(uri), "rb") as stream:
            return pd.read_parquet(stream, **kwargs)

    def storage_status(self) -> dict[str, object]:
        """供 readiness/操作介面顯示，不回傳憑證內容。"""
        return {
            "provider": self.settings.storage_scheme,
            "root": self.settings.data_root,
            "rawdataExists": self.fs.exists(self._storage_path(self.settings.rawdata_dir)),
        }

    def _cached(self, key: str, loader) -> pd.DataFrame:
        """小表只載入一次；double-checked locking 避免併發重複讀檔。"""
        if key not in self._small_tables:
            with self._lock:
                if key not in self._small_tables:
                    self._small_tables[key] = loader()
        return self._small_tables[key]

    @functools.cached_property
    def _file_index(self) -> dict[str, dict[str, object]]:
        """掃 rawdata/ 與 table2/ 建立 INGOT_NO -> 檔案路徑與分組的索引。"""
        index: dict[str, dict[str, object]] = {}

        raw_pattern = self._storage_path(
            self.settings.data_path("rawdata", "g[1-4]", "*.parquet")
        )
        for path in sorted(self.fs.glob(raw_pattern)):
            p = PurePosixPath(path)
            group = p.parent.name
            ingot_no = p.stem.removesuffix(f"_{group}")
            index[ingot_no] = {"group": group, "series": path, "events": None}

        event_pattern = self._storage_path(
            self.settings.data_path("table2", "g[1-4]", "*.parquet")
        )
        for path in sorted(self.fs.glob(event_pattern)):
            p = PurePosixPath(path)
            group = p.parent.name
            ingot_no = p.stem.removesuffix(f"_{group}_table2")
            if ingot_no in index:
                index[ingot_no]["events"] = path

        return index

    def has_ingot(self, ingot_no: str) -> bool:
        return ingot_no in self._file_index

    def series_columns(self) -> list[str]:
        """讀任一根晶棒的 schema 取欄位名，不載入資料列。"""
        import pyarrow.parquet as pq

        first = next(iter(self._file_index.values()))
        with self.fs.open(first["series"], "rb") as stream:
            return list(pq.read_schema(stream).names)

    # ---------- 目錄 ----------

    def list_ingots(self) -> pd.DataFrame:
        return self._cached("ingots", self._read_ingots)

    def _read_ingots(self) -> pd.DataFrame:
        frames = []
        for group, path in self.settings.group_csv_paths.items():
            if not self.fs.exists(self._storage_path(path)):
                continue
            df = self._read_csv(path)
            df["GROUP"] = group
            frames.append(df)

        if not frames:
            return pd.DataFrame()

        catalog = pd.concat(frames, ignore_index=True)
        catalog["CREATETIME"] = pd.to_datetime(catalog["CREATETIME"], errors="coerce")

        # 目錄 csv 可能列到沒有逐點檔的晶棒，只保留實際有資料的。
        # 分組以檔案目錄（＝parquet 內的 DATASET_TYPE）為準：分組 csv 的 GROUP
        # 有部分與逐點資料不一致，這裡一律用權威來源覆寫，並去除跨 csv 的重複。
        index = self._file_index
        catalog = catalog[catalog["INGOT_NO"].isin(index)].copy()
        catalog["GROUP"] = catalog["INGOT_NO"].map(lambda x: index[x]["group"])
        catalog = catalog.drop_duplicates("INGOT_NO", keep="first")
        catalog["DATABASE_NAME"] = catalog["INGOT_NO"].map(
            lambda x: f"Furnace_{x[:2]}"
        )
        return catalog.sort_values("CREATETIME", ascending=False, na_position="last")

    # ---------- 逐點資料 ----------

    def load_series(self, ingot_no: str) -> pd.DataFrame:
        return self._series_cache(ingot_no)

    def _read_series(self, ingot_no: str) -> pd.DataFrame:
        entry = self._file_index.get(ingot_no)
        if entry is None:
            raise KeyError(ingot_no)
        with self.fs.open(entry["series"], "rb") as stream:
            df = pd.read_parquet(stream)
        return df.sort_values(TIME_COLUMN).reset_index(drop=True)

    def load_events(self, ingot_no: str) -> pd.DataFrame:
        entry = self._file_index.get(ingot_no)
        if entry is None:
            raise KeyError(ingot_no)
        if entry["events"] is None:
            return pd.DataFrame()
        with self.fs.open(entry["events"], "rb") as stream:
            return pd.read_parquet(stream).sort_values("RECORDTIME")

    # ---------- 小表 ----------

    def load_segments(self) -> pd.DataFrame:
        def loader() -> pd.DataFrame:
            df = self._read_parquet(self.settings.segment_summary_path)
            for col in ("START_TIME", "END_TIME"):
                df[col] = pd.to_datetime(df[col], errors="coerce")
            return df

        return self._cached("segments", loader)

    def load_precursor_windows(self) -> pd.DataFrame:
        return self._cached(
            "precursor_windows",
            lambda: self._read_csv(self.settings.precursor_windows_path),
        )

    def load_precursor_auc(self) -> pd.DataFrame:
        return self._cached(
            "precursor_auc",
            lambda: self._read_csv(self.settings.precursor_auc_path),
        )

    def load_precursor_sweep(self) -> pd.DataFrame:
        return self._cached(
            "precursor_sweep",
            lambda: self._read_csv(self.settings.precursor_sweep_path),
        )

    def load_profile_band(self) -> pd.DataFrame:
        return self._cached(
            "profile_band",
            lambda: self._read_csv(self.settings.profile_band_path),
        )

    def load_profile_scores(self) -> pd.DataFrame:
        return self._cached(
            "profile_scores",
            lambda: self._read_csv(self.settings.profile_scores_path),
        )
