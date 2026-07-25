from fastapi import APIRouter, HTTPException, Query

from app.api.deps import PrecursorDep

router = APIRouter(prefix="/precursor", tags=["precursor"])


@router.get("/overview")
def overview(service: PrecursorDep):
    return service.overview()


@router.get("/ranking")
def ranking(
    service: PrecursorDep,
    signal: list[str] | None = Query(default=None),
    feature: list[str] | None = Query(default=None),
    minDiscriminance: float = Query(default=0.0, ge=0.0, le=1.0),
):
    """線上重算 AUC 排行；不帶參數即為全特徵掃描。"""
    return service.ranking(
        signals=signal, features=feature, min_discriminance=minDiscriminance
    )


@router.get("/detail")
def detail(service: PrecursorDep, key: str = Query(..., description="如 PIDSL_temp1::sd")):
    try:
        return service.detail(key)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"沒有這個特徵：{key}")


@router.get("/sweep")
def sweep(service: PrecursorDep, signal: str | None = None, feature: str | None = None):
    return service.sweep(signal, feature)


@router.get("/offline-auc")
def offline_auc(service: PrecursorDep):
    return service.offline_auc()
