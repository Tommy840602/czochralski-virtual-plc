# Hetzner 部署指南（共享 VM，三專案共存）

架構：一台 VM，一個共享 Caddy 反向代理（擁有 80/443、自動 HTTPS），
每個專案是獨立 docker compose 栈，接到共享的 `web` 網路，Caddy 依網域路由。
本 PLC 平台不對主機發布端口，只有 Caddy 對外。

```
        :80/:443
   ┌────────────────┐   web 網路
DNS→│ Caddy (共享)   │──┬── plc_frontend:80  (本專案)
   └────────────────┘  ├── project2_...
      自動 TLS          └── project3_...
```

## 前置

- Hetzner Cloud 伺服器（建議 CAX21 ARM / CPX21，≥ 4GB RAM），Ubuntu 22.04/24.04
- 一個網域，DNS A 記錄 `plc.tommy-huang.dev` → 伺服器 IP（Caddy 自動簽 TLS 需要）
- 本機能 SSH 到伺服器

## 一次性：伺服器初始化

```bash
ssh root@伺服器IP

# Docker
curl -fsSL https://get.docker.com | sh

# 防火牆：只開 22/80/443（Hetzner Cloud Firewall 或 ufw）
ufw allow 22 && ufw allow 80 && ufw allow 443 && ufw --force enable

# 共享反向代理網路（三專案共用，只建一次）
docker network create web
# Plant Simulator 與 PLC 共用的內部工控網路
docker network create cz-industrial
```

## 一次性：起共享 Caddy 反向代理

```bash
# 把 deploy/proxy/ 傳到伺服器，例如 /srv/proxy
scp -r deploy/proxy root@伺服器IP:/srv/proxy
ssh root@伺服器IP
cd /srv/proxy
# Caddyfile 已設 plc.tommy-huang.dev；另兩個專案之後在此加 block 即可
nano Caddyfile
docker compose up -d
```

## 部署本 PLC 平台

```bash
# 1) 傳程式碼（用 git 或 scp/rsync）
ssh root@伺服器IP 'mkdir -p /srv/plc'
git clone https://github.com/Tommy840602/czochralski-plc-research.git /srv/plc/app
# 或： rsync -av --exclude node_modules --exclude .venv plc-research/ root@伺服器IP:/srv/plc/app/

# 2) 傳資料（232MB，只需一次；資料不進 git）
rsync -av --exclude='plc-research' --exclude='.DS_Store' \
  /你本機/output/  root@伺服器IP:/srv/plc/data/
# 傳完伺服器上應有 /srv/plc/data/rawdata、table2、segment_summary.parquet …

# 3) 設定環境
ssh root@伺服器IP
cd /srv/plc/app
cp deploy/.env.prod.example .env.prod
nano .env.prod        # 設 DATA_ROOT=/srv/plc/data、帳密、PLC_AUTH_SECRET（openssl rand -hex 32）

# 4) 起服務（讀 .env.prod）
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

## 上線檢查

```bash
# 後端健康（容器內）
docker exec plc_frontend wget -qO- http://backend:8000/api/readyz

# 對外
curl -I https://plc.tommy-huang.dev        # 應 200，Caddy 已簽 TLS
```

瀏覽器開 `https://plc.tommy-huang.dev`，用 `.env.prod` 設定的帳密登入。

## 更新版本

```bash
cd /srv/plc/app
git pull --ff-only
bash scripts/deploy-hetzner.sh
```

## GitHub Actions 自動部署

合併或 push 到 `main` 後，CI 會先完成 backend、frontend 與 deployment
validation；三者都成功才執行 production deploy。請在 GitHub 的
`production` environment 設定：

| Secret | 內容 |
| --- | --- |
| `HETZNER_HOST` | VM IP 或 hostname |
| `HETZNER_USER` | SSH 使用者；需可執行 Docker，並可免密 sudo 更新 `/var/www/plc-frontend` |
| `HETZNER_SSH_KEY` | 對應 VM authorized key 的私鑰 |
| `HETZNER_KNOWN_HOSTS` | `ssh-keyscan -H <host>` 的固定輸出 |
| `HETZNER_PORT` | 選填，預設 `22` |
| `HETZNER_APP_DIR` | 選填，預設 `/srv/plc/app` |
| `SIMULATOR_REPO_SSH_KEY` | `czochralski-simulator` private repo 的唯讀 deploy key |
| `PLC_AUTH_USERNAME` | Production 登入帳號，不可使用 `admin` |
| `PLC_AUTH_ENGINEER_USERNAME` | Engineer 登入帳號，預設 `plc.engineer` |
| `PLC_AUTH_LEAD_USERNAME` | Lead 登入帳號，預設 `plc.lead` |
| `PLC_AUTH_PASSWORD` | Production 登入密碼，至少 12 字元 |
| `PLC_AUTH_SECRET` | Token 簽章金鑰，至少 32 字元的隨機值 |

GitHub Actions 會自動建立 `HETZNER_APP_DIR`（預設 `/srv/plc/app`），並將
已通過 CI 的 `main` 工作目錄同步進去，不需要 VM 具備 GitHub repository
存取權。同步會保留 VM 專案根目錄既有的 `.env.hetzner`，再以 GitHub
production secrets 更新 PLC 帳密與 runtime 連線設定，不會在日誌輸出密碼。
若 VM 已有 PLC 部署，一次性 bootstrap 仍可從既有環境檔或 backend 容器遷移。
Production workflow 會從獨立 private repo 同步並先啟動 Plant Simulator；
其 Compose 會建立 `cz-industrial` network，通過 `/healthz` 後才部署 PLC。
缺少 GitHub secrets 時 deploy job 會顯示 warning 並安全跳過，不影響 CI。

## 資源與共存

- 後端 `mem_limit: 640m`、前端 `128m`，`restart: unless-stopped`
- 資料 232MB 唯讀掛載，不進映像檔；本專案穩定佔用 ~400MB，不影響另外兩個專案
- 另兩個專案照同模式（接 `web` 網路 + 在 Caddyfile 加 block）即可共存

## 沒有網域先測試

把 `Caddyfile` 的 `plc.tommy-huang.dev { … }` 換成 `:80 { reverse_proxy plc_frontend:80 }`，
用 `http://伺服器IP` 直接訪問（無 HTTPS）。之後有網域再改回。
