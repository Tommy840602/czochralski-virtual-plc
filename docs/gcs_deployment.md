# GCS 部署驗證報告

驗證平台後端從 `gs://ingot` 讀取資料的可行性。**結論：後端程式正確，卡在 GCP 側
（計費停用 + 資料未傳完），非程式問題。**

## 驗證結果

| 檢查項 | 結果 | 說明 |
| --- | --- | --- |
| gcsfs + ADC 認證 | ✅ | ADC（tommy840602@gmail.com）可認證 |
| rawdata glob 列舉 | ✅ | `gs://ingot/rawdata/g[1-4]/*.parquet` 正確列出 **209 個** parquet，命名/層級皆符合後端預期 |
| 物件內容讀取 | ❌ | **403 The billing account for the owning project is disabled in state closed** |
| MCP 工具交叉驗證 | ❌ | 獨立認證讀同一物件同樣 403 → 確認為專案級封鎖，非後端認證問題 |
| 根目錄資料檔 | ⚠️ | bucket 僅有 `rawdata/`、`table2/`；根目錄 parquet/CSV 尚未上傳 |

後端 `repositories/parquet_repo.py`（fsspec + gcsfs）在**列舉層**已驗證可運作；
`config.py` 的 `PLC_DATA_ROOT=gs://ingot` 路徑組合正確。唯物件下載被 GCP 阻斷。

## 阻斷點（皆需在 GCP 側處理）

### 1. 計費停用（硬阻斷）

bucket `ingot` 所屬專案 `ingot-503123` 的 billing account 為 `closed`，
GCS 拒絕一切物件資料下載（egress）。

**修復**：GCP Console → Billing → 對專案 `ingot-503123` 重新連結有效計費帳戶。

### 2. 根目錄資料未上傳

目前只有 `rawdata/`、`table2/`。後端還需要根目錄這些檔：

```
segment_summary.parquet
precursor_windows.csv  precursor_auc.csv  precursor_sweep.csv
profile_band.csv  profile_scores.csv
G1_single_no_fault.csv  G2_single_with_fault.csv
G3_multi_with_fault.csv  G4_multi_no_fault.csv
```

**上傳**（於 output/ 目錄）：

```bash
gcloud storage cp \
  segment_summary.parquet precursor_windows.csv precursor_auc.csv \
  precursor_sweep.csv profile_band.csv profile_scores.csv \
  G1_single_no_fault.csv G2_single_with_fault.csv \
  G3_multi_with_fault.csv G4_multi_no_fault.csv \
  gs://ingot/
# 順手清掉 macOS 垃圾
gcloud storage rm gs://ingot/rawdata/.DS_Store gs://ingot/table2/.DS_Store 2>/dev/null || true
```

### 3. 服務帳戶權限（上線時）

執行後端的服務帳戶（Cloud Run/GCE/GKE 的 SA，或本機 ADC）需要 bucket 的
`roles/storage.objectViewer`。

## 計費修復後的驗證步驟

```bash
cd cz-virtual-plc/backend
PLC_DATA_ROOT=gs://ingot PLC_GCS_PROJECT=ingot-503123 \
  .venv/bin/python -m uvicorn app.main:app --port 8000
# 健康檢查應回 provider=gcs、rawdataExists=true
curl localhost:8000/api/health
```

`main.py` 的 `/api/health` 已能回報 GCS 連線狀態（provider/root/rawdataExists），
計費恢復後即可用它做 readiness 驗證。全部 8 頁的資料端點屆時應正常。
