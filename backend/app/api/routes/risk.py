from fastapi import APIRouter, HTTPException

from app.api.deps import RiskDep

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/board")
def board(service: RiskDep):
    """所有 BODY 段的風險看板：監控偵測風險 + 時間先驗 + 分級 + 驗證。"""
    return service.board()


@router.get("/hazard-curve")
def hazard_curve(service: RiskDep):
    return service.hazard_curve()


@router.get("/ingots/{ingot_no}")
def ingot(ingot_no: str, service: RiskDep):
    try:
        return service.ingot(ingot_no)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"找不到晶棒 {ingot_no} 的 BODY 段")
