from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.core.config import get_settings
from app.core.security import check_credentials, create_token

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginRequest):
    s = get_settings()
    if not check_credentials(body.username, body.password, s.auth_username, s.auth_password):
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
    token, exp = create_token(body.username, s.auth_secret, s.token_ttl_hours * 3600)
    return {"token": token, "expiresAt": exp, "username": body.username}


@router.get("/me")
def me(user: CurrentUser):
    """驗證目前 token 是否有效，回傳使用者。"""
    return {"username": user}
