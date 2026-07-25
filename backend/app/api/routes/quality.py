from fastapi import APIRouter

from app.api.deps import QualityDep

router = APIRouter(prefix="/quality", tags=["quality"])


@router.get("/phase-risk")
def phase_risk(service: QualityDep):
    """各相位斷線率與 Kaplan-Meier 生存曲線。"""
    return service.phase_risk()


@router.get("/furnace-risk")
def furnace_risk(service: QualityDep):
    return service.furnace_risk()


@router.get("/fusion")
def fusion(service: QualityDep):
    """監控融合：PC1/PC2 提升召回的分析。"""
    return service.fusion()
