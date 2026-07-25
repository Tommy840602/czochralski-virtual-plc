import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.api.deps import SeriesDep

router = APIRouter(tags=["series"])


@router.get("/ingots/{ingot_no}/series")
def ingot_series(
    ingot_no: str,
    service: SeriesDep,
    signal: list[str] = Query(..., description="訊號名，可重複指定"),
    start: str | None = None,
    end: str | None = None,
    segmentSeq: int | None = None,
    maxPoints: int | None = Query(default=None, ge=100, le=20000),
):
    try:
        return service.series(
            ingot_no,
            signals=signal,
            start=pd.to_datetime(start) if start else None,
            end=pd.to_datetime(end) if end else None,
            segment_seq=segmentSeq,
            max_points=maxPoints,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"找不到晶棒 {ingot_no}")


@router.get("/compare")
def compare(
    service: SeriesDep,
    ingot: list[str] = Query(..., description="要疊圖的晶棒編號"),
    signal: str = Query(...),
    normalize: bool = True,
):
    if len(ingot) > 12:
        raise HTTPException(status_code=400, detail="一次最多疊 12 根晶棒")
    return service.compare(ingot, signal, normalize)
