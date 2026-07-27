from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header, HTTPException

from app.core.config import Settings, get_settings
from app.core.security import AuthenticatedUser, verify_token
from app.repositories.parquet_repo import ParquetRepository
from app.services.catalog_service import CatalogService
from app.services.control_service import ControlService
from app.services.earlywarning_service import EarlyWarningService
from app.services.precursor_service import PrecursorService
from app.services.profile_service import ProfileService
from app.services.quality_service import QualityService
from app.services.risk_service import RiskService
from app.services.series_service import SeriesService

SettingsDep = Annotated[Settings, Depends(get_settings)]


def require_user(authorization: str | None = Header(default=None)) -> AuthenticatedUser:
    """驗證 Bearer token，回傳身份與角色。缺 token 或無效一律 401。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登入", headers={"WWW-Authenticate": "Bearer"})
    token = authorization.removeprefix("Bearer ").strip()
    try:
        return verify_token(token, get_settings().auth_secret)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc), headers={"WWW-Authenticate": "Bearer"})


CurrentUser = Annotated[AuthenticatedUser, Depends(require_user)]


@lru_cache
def get_repository() -> ParquetRepository:
    """單例：repository 內含快取，不能每次請求重建。"""
    return ParquetRepository(get_settings())


def get_catalog_service() -> CatalogService:
    return CatalogService(get_repository())


def get_series_service() -> SeriesService:
    return SeriesService(get_repository(), get_settings())


def get_precursor_service() -> PrecursorService:
    return PrecursorService(get_repository())


def get_profile_service() -> ProfileService:
    return ProfileService(get_repository())


def get_control_service() -> ControlService:
    return ControlService(get_repository())


def get_earlywarning_service() -> EarlyWarningService:
    return EarlyWarningService(get_repository())


def get_quality_service() -> QualityService:
    return QualityService(get_repository())


def get_risk_service() -> RiskService:
    return RiskService(get_repository())


CatalogDep = Annotated[CatalogService, Depends(get_catalog_service)]
SeriesDep = Annotated[SeriesService, Depends(get_series_service)]
PrecursorDep = Annotated[PrecursorService, Depends(get_precursor_service)]
ProfileDep = Annotated[ProfileService, Depends(get_profile_service)]
ControlDep = Annotated[ControlService, Depends(get_control_service)]
EarlyWarningDep = Annotated[EarlyWarningService, Depends(get_earlywarning_service)]
QualityDep = Annotated[QualityService, Depends(get_quality_service)]
RiskDep = Annotated[RiskService, Depends(get_risk_service)]
