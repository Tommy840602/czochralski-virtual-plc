# CZ Virtual PLC

> 獨立 Plant Simulator 的控制中樞：透過 OPC UA 掃描 Sensor/I/O，執行
> Interlock、Sequence 與 Local Control，再將可信任的 PLC 資料交給 DCS。
> 原有的 CZ 時序資料分析、預警與品質功能完整保留。

🔗 **Live Demo**：[plc.tommy-huang.dev](https://plc.tommy-huang.dev)（展示帳號 `admin`，密碼請洽作者）

![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Vue 3](https://img.shields.io/badge/Vue_3-4FC08D?logo=vuedotjs&logoColor=white)
![ECharts](https://img.shields.io/badge/ECharts-AA344D?logo=apacheecharts&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
![GCS](https://img.shields.io/badge/Google_Cloud_Storage-4285F4?logo=googlecloud&logoColor=white)
![OPC UA](https://img.shields.io/badge/OPC_UA-1.1.8-3fb6ad)

---

## ⚙️ Virtual PLC Runtime

```text
Plant Simulator ⇄ Virtual PLC → DCS → Historian → SPC
   Sensor / I/O     Control     Operations      Quality
```

本 repo 現在是架構中的 PLC 責任邊界：

- 以固定週期讀取 `Plant.*` 與 `Status.*` OPC UA tags，建立 PLC input image。
- 檢查 OPC UA、通訊、資料品質、安全門與 E-Stop interlocks。
- 依 `MELT → STABILIZE → SEED → NECK → CROWN → BODY → TAIL`
  製程階段輸出 actuator 命令。
- BODY 階段執行溫度與直徑的本機控制邏輯。
- 聯鎖跳脫或通訊錯誤時，強制 heater、rotation、pull speed 等輸出歸零。
- `/plc` 操作頁提供 START / STOP / RESET、I/O image、聯鎖與 alarm 監看。
- `/api/plc/status`、`/api/plc/tags`、`/api/plc/commands/{command}`
  皆受既有登入驗證保護。
- 登入提供 `Operator / Engineer / Lead` 三種 PLC 身份；角色寫入 HMAC token。
  Operator 可執行標準啟停，RESET 僅允許 Engineer 與 Lead。
- 登入頁可自助申請三種角色；新帳號先進入 `PENDING`，由 PLC Lead 在「帳號申請」
  核准或駁回。身份與 append-only 稽核事件持久化於 PostgreSQL，核准前不得登入。

Plant Simulator 仍獨立維護於
[`Tommy840602/czochralski-simulator`](https://github.com/Tommy840602/czochralski-simulator)；
它只負責設備物理、Sensor、Actuator 與故障模擬，不執行 PLC 控制邏輯。

---

## ✨ 平台亮點

這不是一個「跑出高 AUC 就收工」的展示，而是一套**誠實面對資料的分析系統**：

- **抓得住混淆**：發現「斷線可預測性」被**段時長**支配（光用段長分斷線 AUC 0.92–0.95）。
  以**配對世代設計**（同生長階段 + 同群體）去除混淆後，誠實揭露真實前兆訊號其實只有短程
  （提前 20 分 AUC ~0.75，40 分外衰減至接近隨機）。
- **不誇大模型**：多變量預警模型（按晶棒分組交叉驗證）誠實呈現**未超越單一特徵**——
  並用過擬合曲線把 p≫n 的道理攤開給人看，而非藏起來。
- **控制器逆向工程**：從資料驗證直徑控制律，指出其只有 **3 個等效增益**、被控對象在閉環
  資料下**不可辨識**（故不謊稱能求最優），並揪出 Er_M 非線性的死區與跳變。
- **可分層替換的架構**：資料來源（本機檔案 / GCS）透過 repository 抽象一鍵切換，
  service 與 API 不動。
- **已上線**：Docker 化部署於 Hetzner，與另一專案共存於共享 VM、共用 GCS 資料源，
  主機 nginx + 自動 TLS。公開 `/api/livez`、`/api/readyz` 僅回低敏感度狀態；
  含 GCS provider/root 的 `/api/health` 必須登入。

---

## 🧭 功能總覽（Virtual PLC Runtime + 8 個工程分析頁）

| 頁面 | 內容 |
| --- | --- |
| **PLC Runtime** | OPC UA 連線、PLC scan、I/O image、Interlock、Sequence、Local Control、Alarm 與操作命令 |
| **總覽** | 分組分布、各爐台晶棒／異常數、斷線發生的製程階段 |
| **晶棒探索** | 依分組／爐台／異常狀態篩選；單棒逐點訊號檢視（NECK/CROWN/BODY/TAIL 相位色帶、多訊號疊圖、LTTB 降採樣、切段表）|
| **前兆分析** | 斷線前視窗特徵鑑別力排行（線上重算 Mann-Whitney AUC + BH-FDR）、ROC 與 case/control 分布 |
| **預警模型** | 多變量斷線風險模型（L2 邏輯迴歸，分組 CV）；過擬合曲線、ROC/PR、可調閾值操作點、前置時間衰減 |
| **輪廓監控** | 功率包絡帶偏離、T²/SPE/LEVEL 管制越界（OOC），OOC vs. 實際斷線混淆矩陣 |
| **控制調參** | 直徑控制器（拉速 PID）開環 replay：調 Gp/Gv/Gd 看 MV 指令差異、Er_M 死區/跳變審查 |
| **品質分析** | 相位斷線率與 BODY Kaplan-Meier 生存曲線、監控融合（PC1/PC2 把召回 5%→77%）、爐台比較 |
| **運營風險** | 每段/每晶棒風險回顧：監控偵測（回溯）與時間先驗（KM hazard，可即時）**分開標示**，風險看板 + 下鑽 |

---

## 🏗 系統架構

```
 Plant Simulator ── OPC UA ──► Virtual PLC Runtime
       ▲                           │
       └──── actuator outputs ─────┘
                                   │ authenticated API
                    Browser (Vue 3 + ECharts)
                            │  HTTPS
                    ┌───────▼────────┐
                    │  nginx + certbot │  靜態前端 + 反代 /api、自動 TLS
                    └───────┬────────┘
                            │  127.0.0.1:8000
                    ┌───────▼────────┐
                    │  FastAPI (分層) │
                    │  Virtual PLC runtime + analytics services
                    └───────┬────────┘
                            │  fsspec
                    ┌───────▼────────┐
                    │  Parquet/CSV    │  本機目錄 或 gs://（一鍵切換）
                    └────────────────┘
```

**後端分層**（`backend/app/`）：`plc/` 是 OPC UA adapter、tag contract、
scan runtime 與 I/O model；`repositories/base.py` 是分析資料抽象契約，
`parquet_repo` 以 fsspec 讀本機或 GCS 並含 LRU 快取；`services/` 為純運算；
`api/routes/` 只做參數轉換與錯誤碼。要換 DuckDB/Postgres 只需實作介面、改 `deps`。

**技術棧**：FastAPI · asyncua / OPC UA · Vue 3 · Vue Router · Pinia · ECharts · pandas / numpy / scipy ·
PostgreSQL 17 · fsspec / gcsfs · Docker · nginx · Let's Encrypt。分析用純 numpy/scipy 手寫
（IRLS 邏輯迴歸、Mann-Whitney、BH-FDR、Kaplan-Meier、LTTB），不依賴 scikit-learn。

### 身份與帳號申請

PLC 人員角色為 `Operator / Engineer / Lead`。申請帳號後一律先進入 `PENDING`，
只能由 Lead 在「帳號申請」核准或駁回；申請人不得在核准前登入。帳號、密碼雜湊、
狀態與 append-only 身份稽核帳本都以 PostgreSQL 為唯一權威，不使用瀏覽器角色欄位
或本機檔案判斷權限。正式部署的 PostgreSQL volume 與應用 release 分離，重部署不會
重建帳號。

---

## 🔬 分析深度（誠實的方法學）

完整推理鏈記錄於 [`docs/`](docs/)：

| 文檔 | 主題 |
| --- | --- |
| [control_analysis.md](docs/control_analysis.md) | 控制器辨識：3 等效增益、被控對象不可辨識、Er_M 審查 |
| [excitation_experiment.md](docs/excitation_experiment.md) | 要真最優增益所需的激勵實驗設計 |
| [earlywarning_analysis.md](docs/earlywarning_analysis.md) | 多變量預警：為何未超越單特徵（p≫n） |
| [body_break_confound_audit.md](docs/body_break_confound_audit.md) | 斷線預測的混淆稽核：段時長支配、配對世代結果 |
| [gcs_deployment.md](docs/gcs_deployment.md) | GCS 資料源驗證報告 |

分析管線 [`analysis/matched_break_pipeline.py`](analysis/matched_break_pipeline.py) 可重現。

---

## 🚀 本機執行

```bash
# 後端（埠 8000）
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
PLC_DATA_ROOT=/path/to/data .venv/bin/python -m uvicorn app.main:app --reload

# 前端（埠 5173，dev proxy 轉 /api 給後端）
cd frontend
npm install && npm run dev
```

或一鍵 Docker：`docker compose up --build`（開 http://localhost:8080）。
資料根目錄可為本機路徑或 `gs://bucket/prefix`，由 `PLC_DATA_ROOT` 切換。

### 與獨立 Plant Simulator 整合

兩個 repo 保持獨立部署，但加入同一個內部 Docker network：

```bash
# terminal 1：czochralski-simulator repo
docker compose up -d --build

# terminal 2：本 repo
docker compose -f docker-compose.yml -f docker-compose.runtime.yml up -d --build
```

Simulator 會建立 `cz-industrial` network；PLC backend 透過
`plant-simulator:4840` 讀寫 OPC UA，不需把 OPC UA 暴露到公網。
登入後開啟 <http://localhost:8080/plc> 即可操作。

聯鎖採 stop-dominant：任何 blocking interlock 跳脫時，PLC 會清除 run request、
寫入安全輸出；條件恢復後也不會自動重啟，必須由操作者再次下達 START。

PLC 同時讀取 Plant 的 `Status.CycleId`、`Status.IngotId` 與
`Status.CycleOutcome`，並透過 `cz.plc.dcs.telemetry.v2` 原樣送往 DCS。
Plant 回報 `COMPLETED` 或 `ABORTED` 時，PLC 會清除 run request；DCS/SPC
因此能以真實 cycle 身分區分正常完成與中止批次。

---

## ☁ 部署（Hetzner，與 SPC 共享 VM）

已上線於 Hetzner Cloud，與另一專案（SPC）共存於同一台 VM、**共用 GCS 資料源**：

- 後端容器監聽 `127.0.0.1:8000`，讀 `gs://`（fsspec + SA 金鑰）
- 主機 nginx 托管前端 dist + 反代 `/api`，certbot 自動 TLS
- 資源隔離（`mem_limit`），兩專案互不干擾
- `PLC_ENVIRONMENT=production` 啟動前拒絕預設帳號、短密碼、弱簽章金鑰與萬用 CORS
- 身份、帳號申請與稽核由 PostgreSQL 17 volume 保存；首次部署自動產生並持久化
  `PLC_DB_PASSWORD`，後續 release 沿用同一密碼

完整步驟見 [`deploy/DEPLOY.md`](deploy/DEPLOY.md)。

Push/merge 到 `main` 會先跑完整 CI；CI 全部成功且 GitHub `production`
environment 已設定 Hetzner SSH secrets 時，才會自動更新 VM。部署腳本會
更新 backend、前端靜態檔並執行 liveness check。

---

## 📁 專案結構

```
backend/app/
  plc/           OPC UA adapter、Tag contract、I/O model、scan runtime
  core/          設定、訊號分類與相位定義、簽章 token
  repositories/  抽象契約 → parquet_repo（fsspec 本機/GCS + LRU）
  services/      catalog / series / precursor / profile / control
                 earlywarning / quality / risk（純運算）
  api/routes/    薄 HTTP 層 + JWT 保護
frontend/src/
  views/         Virtual PLC Runtime + 8 個工程分析頁 + 登入
  composables/   theme（日夜）、useAsync、format
  components/     EChart（主題感知薄封裝）、StateBlock
analysis/        配對世代斷線分析管線
docs/            分析文檔與混淆稽核
deploy/          Hetzner 部署（nginx conf、指南、上傳腳本）
```
