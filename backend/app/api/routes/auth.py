from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.core.config import get_settings
from app.core.security import ROLE_PERMISSIONS, UserRole, check_credentials, create_token

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginRequest):
    s = get_settings()
    identity = next(
        (
            (username, UserRole(role_name))
            for username, role_name in s.auth_identities.items()
            if check_credentials(body.username, body.password, username, s.auth_password)
        ),
        None,
    )
    if identity is None:
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
    username, role = identity
    token, exp = create_token(
        username,
        s.auth_secret,
        s.token_ttl_hours * 3600,
        role,
    )
    return {
        "token": token,
        "expiresAt": exp,
        "username": username,
        "role": role.value,
        "permissions": list(ROLE_PERMISSIONS[role]),
    }


@router.get("/me")
def me(user: CurrentUser):
    """驗證目前 token 是否有效，回傳使用者。"""
    return {
        "username": user.username,
        "role": user.role.value,
        "permissions": list(user.permissions),
    }
