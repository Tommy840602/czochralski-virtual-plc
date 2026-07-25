from fastapi import APIRouter, HTTPException, Query

from app.api.deps import ControlDep

router = APIRouter(prefix="/control", tags=["control"])


@router.get("/defaults")
def defaults(service: ControlDep):
    """當前 recipe 的等效增益、常數、Er_M 曲線。"""
    return service.defaults()


@router.get("/replay")
def replay(
    service: ControlDep,
    ingot: str = Query(...),
    segmentSeq: int | None = None,
    gp: float = 0.0004,
    gv: float = 0.16,
    gd: float = -0.1064,
    ermMode: str = Query("default", pattern="^(default|monotone)$"),
):
    """開環 replay：同一記錄工況下，比較不同增益的控制器 MV 指令。"""
    try:
        return service.replay(ingot, segmentSeq, gp, gv, gd, ermMode)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0]))
