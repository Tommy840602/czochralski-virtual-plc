from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import get_repository, require_user
from app.api.routes import (
    auth,
    catalog,
    control,
    earlywarning,
    precursor,
    profile,
    quality,
    risk,
    series,
)
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="長晶爐 PLC 研究平台",
    description="CZ 長晶製程 PLC 時序資料的探索、前兆分析與輪廓監控",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# 登入端點本身不需授權
app.include_router(auth.router, prefix="/api")

# 其餘資料端點一律需要有效 token
for router in (
    catalog.router,
    series.router,
    precursor.router,
    profile.router,
    control.router,
    earlywarning.router,
    quality.router,
    risk.router,
):
    app.include_router(router, prefix="/api", dependencies=[Depends(require_user)])


@app.get("/api/health")
def health():
    try:
        storage = get_repository().storage_status()
        return {"status": "ok", **storage}
    except Exception as exc:
        # API 仍活著，但資料來源尚未授權/設定完成；讓 readiness 能辨識此狀態。
        return {
            "status": "degraded",
            "provider": settings.storage_scheme,
            "root": settings.data_root,
            "rawdataExists": False,
            "storageError": type(exc).__name__,
        }
