from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CatalogDep

router = APIRouter(tags=["catalog"])


@router.get("/meta")
def meta(service: CatalogDep):
    """訊號清單與分組定義，前端啟動時取一次。"""
    return {**service.signal_meta(), **service.facets()}


@router.get("/summary")
def summary(service: CatalogDep):
    return service.summary()


@router.get("/ingots")
def list_ingots(
    service: CatalogDep,
    group: list[str] | None = Query(default=None),
    furnace: list[str] | None = Query(default=None),
    hasFault: bool | None = None,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=25, ge=1, le=200),
):
    return service.list_ingots(
        groups=group,
        furnaces=furnace,
        has_fault=hasFault,
        keyword=q,
        page=page,
        page_size=pageSize,
    )


@router.get("/ingots/{ingot_no}")
def ingot_detail(ingot_no: str, service: CatalogDep):
    try:
        return service.ingot_detail(ingot_no)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"找不到晶棒 {ingot_no}")


@router.get("/ingots/{ingot_no}/events")
def ingot_events(ingot_no: str, service: CatalogDep):
    try:
        return service.ingot_events(ingot_no)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"找不到晶棒 {ingot_no}")
