from fastapi import APIRouter, HTTPException, Query

from app.api.deps import ProfileDep

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/band")
def band(service: ProfileDep):
    return service.band()


@router.get("/scores")
def scores(
    service: ProfileDep,
    onlyOoc: bool = False,
    endedBy: list[str] | None = Query(default=None),
    clean: bool | None = None,
):
    return service.scores(only_ooc=onlyOoc, ended_by=endedBy, clean=clean)


@router.get("/confusion")
def confusion(service: ProfileDep):
    return service.confusion()


@router.get("/ingots/{ingot_no}")
def ingot_profile(ingot_no: str, service: ProfileDep, segmentSeq: int | None = None):
    try:
        return service.ingot_profile(ingot_no, segmentSeq)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"沒有輪廓資料：{exc.args[0]}")
