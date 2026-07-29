from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser
from app.core.config import get_settings
from app.core.security import ROLE_PERMISSIONS, UserRole, create_token
from app.repositories.identity_store import get_identity_store

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    username: str = Field(min_length=3, max_length=40)
    email: str = Field(min_length=3, max_length=254)
    role: UserRole
    password: str = Field(min_length=12, max_length=72)


def _client_ip(request: Request) -> str:
    return request.headers.get("x-real-ip") or (
        request.client.host if request.client else "?"
    )


@router.post("/login")
def login(body: LoginRequest):
    s = get_settings()
    identity = get_identity_store().verify(body.username, body.password)
    if identity is None:
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
    username = str(identity["username"])
    role = UserRole(str(identity["role"]))
    token, exp = create_token(
        username,
        s.auth_secret,
        s.token_ttl_hours * 3600,
        role,
        int(identity["authVersion"]),
    )
    return {
        "token": token,
        "expiresAt": exp,
        "username": username,
        "role": role.value,
        "permissions": list(ROLE_PERMISSIONS[role]),
    }


@router.post("/register", status_code=201)
def register(body: RegisterRequest, request: Request):
    try:
        return get_identity_store().register(
            username=body.username,
            name=body.name,
            email=str(body.email),
            role=body.role,
            password=body.password,
            source_address=_client_ip(request),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _require_access_lead(user: CurrentUser) -> None:
    if not user.can("access:manage"):
        raise HTTPException(status_code=403, detail="此操作限 PLC Lead 執行")


@router.get("/requests")
def requests(user: CurrentUser):
    _require_access_lead(user)
    store = get_identity_store()
    return {"requests": store.pending(), "audit": store.audit()}


@router.post("/requests/{username}/approve")
def approve(username: str, request: Request, user: CurrentUser):
    _require_access_lead(user)
    try:
        return get_identity_store().decide(
            username,
            approve=True,
            actor=user.username,
            source_address=_client_ip(request),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/requests/{username}/reject")
def reject(username: str, request: Request, user: CurrentUser):
    _require_access_lead(user)
    try:
        return get_identity_store().decide(
            username,
            approve=False,
            actor=user.username,
            source_address=_client_ip(request),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/me")
def me(user: CurrentUser):
    """驗證目前 token 是否有效，回傳使用者。"""
    return {
        "username": user.username,
        "role": user.role.value,
        "permissions": list(user.permissions),
    }
