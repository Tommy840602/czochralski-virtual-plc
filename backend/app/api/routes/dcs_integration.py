from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.plc.dcs_contract import dcs_snapshot
from app.plc.deps import get_plc_runtime

router = APIRouter(prefix="/dcs", tags=["internal-dcs-integration"])


@router.get("/v1/snapshot")
def snapshot():
    """Internal-network-only PLC telemetry consumed by the DCS edge adapter."""
    payload = dcs_snapshot(get_plc_runtime().snapshot())
    return JSONResponse(payload, headers={"Cache-Control": "no-store"})
