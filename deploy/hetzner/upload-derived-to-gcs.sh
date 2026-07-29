#!/usr/bin/env bash
# 把 PLC 的衍生資料檔上傳到 gs://ingot/（rawdata/ 與 table2/ 已在 bucket 內）。
# 在「本機 output/ 目錄」執行（即含這些檔的資料夾）。透過伺服器上 spc-backend 容器
# 的 SA 金鑰寫入 GCS（該金鑰有 create 權限）。
#
#   用法： cd /你的/output && bash cz-virtual-plc/deploy/hetzner/upload-derived-to-gcs.sh
#
# 需可 SSH 到伺服器（金鑰已在 ssh-agent）。

set -euo pipefail
SERVER="${PLC_SERVER:-tommy@167.233.174.12}"
CONTAINER="${PLC_GCS_CONTAINER:-spc-backend-1}"

FILES=(
  segment_summary.parquet
  precursor_windows.csv
  precursor_auc.csv
  precursor_sweep.csv
  profile_band.csv
  profile_scores.csv
  G1_single_no_fault.csv
  G2_single_with_fault.csv
  G3_multi_with_fault.csv
  G4_multi_no_fault.csv
)

for f in "${FILES[@]}"; do
  [ -f "$f" ] || { echo "缺檔: $f"; exit 1; }
  echo -n "上傳 $f … "
  cat "$f" | ssh "$SERVER" "docker exec -e OBJ='ingot/$f' -i $CONTAINER python -c '
import gcsfs, sys, os
fs = gcsfs.GCSFileSystem()
with fs.open(os.environ[\"OBJ\"], \"wb\") as w:
    w.write(sys.stdin.buffer.read())
print(\"ok\", fs.size(os.environ[\"OBJ\"]), \"bytes\")
'"
done
echo "全部上傳完成。"
