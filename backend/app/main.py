from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.deps import get_repository, require_user
from app.api.routes import (
    auth,
    catalog,
    control,
    dcs_integration,
    earlywarning,
    plc_runtime,
    precursor,
    profile,
    quality,
    risk,
    series,
)
from app.core.config import get_settings
from app.plc.deps import get_plc_runtime

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    runtime = get_plc_runtime()
    await runtime.start()
    try:
        yield
    finally:
        await runtime.stop()


app = FastAPI(
    title="CZ Virtual PLC",
    description="長晶爐 Virtual PLC 控制、I/O 聯鎖與製程資料分析平台",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# 登入端點本身不需授權
app.include_router(auth.router, prefix="/api")

# 僅由 cz-industrial Docker 網路上的 DCS adapter 直連；nginx 不代理 /internal。
app.include_router(dcs_integration.router, prefix="/internal")

# 其餘資料端點一律需要有效 token
for router in (
    plc_runtime.router,
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


def _health_payload() -> dict:
    try:
        storage = get_repository().storage_status()
        return {
            **storage,
            "status": "ok" if storage.get("rawdataExists") else "degraded",
        }
    except Exception as exc:
        # API 仍活著，但資料來源尚未授權/設定完成；讓 readiness 能辨識此狀態。
        return {
            "status": "degraded",
            "provider": settings.storage_scheme,
            "root": settings.data_root,
            "rawdataExists": False,
            "storageError": type(exc).__name__,
        }


@app.get("/api/livez")
def livez():
    """Process liveness only; never touches GCS."""
    return JSONResponse({"status": "ok"}, headers={"Cache-Control": "no-store"})


@app.get("/api/readyz")
def readyz():
    """Public readiness with no bucket, path, credential or exception details."""
    payload = _health_payload()
    public = {
        "status": payload["status"],
        "checks": {"storage": bool(payload.get("rawdataExists"))},
    }
    return JSONResponse(
        public,
        status_code=200 if payload["status"] == "ok" else 503,
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/health", dependencies=[Depends(require_user)])
def health():
    """Authenticated detailed diagnostics for operators."""
    return JSONResponse(_health_payload(), headers={"Cache-Control": "no-store"})
