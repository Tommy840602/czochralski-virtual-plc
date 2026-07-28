from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser
from app.plc.deps import get_plc_runtime
from app.plc.models import PlcCommand
from app.plc.tag_contract import tag_contract

router = APIRouter(prefix="/plc", tags=["plc-runtime"])


@router.get("/status")
async def status():
    return get_plc_runtime().snapshot().to_dict()


@router.get("/tags")
async def tags():
    return tag_contract()


@router.post("/commands/{command}")
async def command(command: PlcCommand, user: CurrentUser):
    permission = "plc:reset" if command is PlcCommand.RESET else "plc:operate"
    if not user.can(permission):
        raise HTTPException(
            status_code=403,
            detail=f"{user.role.value} 無權執行 {command.value.upper()}",
        )
    try:
        return (await get_plc_runtime().command(command)).to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
