from fastapi import APIRouter, Query

from app.api.deps import EarlyWarningDep

router = APIRouter(prefix="/earlywarning", tags=["earlywarning"])


@router.get("/overview")
def overview(service: EarlyWarningDep):
    return service.overview()


@router.get("/model")
def model(
    service: EarlyWarningDep,
    lam: float = Query(100.0, ge=0.1, le=1000.0),
    threshold: float | None = Query(None, ge=0.0, le=1.0),
):
    """指定正則化強度下的模型：OOF 表現、風險分數、特徵貢獻、操作點。"""
    return service.model(lam=lam, threshold=threshold)


@router.get("/reg-path")
def reg_path(service: EarlyWarningDep):
    """過擬合曲線：train vs OOF AUC 隨 λ 變化。"""
    return service.reg_path()


@router.get("/lead-curve")
def lead_curve(service: EarlyWarningDep):
    """BODY 斷線前置時間衰減：配對世代 vs naive（離線預算）。"""
    return service.lead_curve()
