"""極簡簽章 token，僅用標準庫（不引入 JWT 相依）。

帳密由設定/環境變數提供，登入後簽發包含角色的 HMAC-SHA256 token，之後每個請求
帶 `Authorization: Bearer <token>`。這不是企業級 IdP，但能為展示環境提供可驗證
的身份與最小 RBAC，且無外部相依。
"""

import base64
from dataclasses import dataclass
from enum import StrEnum
import hashlib
import hmac
import json
import time


class UserRole(StrEnum):
    OPERATOR = "Operator"
    ENGINEER = "Engineer"
    LEAD = "Lead"


ROLE_PERMISSIONS: dict[UserRole, tuple[str, ...]] = {
    UserRole.OPERATOR: ("plc:read", "plc:operate"),
    UserRole.ENGINEER: ("plc:read", "plc:operate", "plc:reset", "analytics:view"),
    UserRole.LEAD: (
        "plc:read",
        "plc:operate",
        "plc:reset",
        "analytics:view",
        "access:manage",
    ),
}


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    username: str
    role: UserRole
    auth_version: int = 1

    @property
    def permissions(self) -> tuple[str, ...]:
        return ROLE_PERMISSIONS[self.role]

    def can(self, permission: str) -> bool:
        return permission in self.permissions


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def create_token(
    username: str,
    secret: str,
    ttl_seconds: int,
    role: UserRole = UserRole.OPERATOR,
    auth_version: int = 1,
) -> tuple[str, int]:
    """回傳 (token, expiresAtEpoch)。"""
    exp = int(time.time()) + ttl_seconds
    body = _b64e(
        json.dumps(
            {
                "sub": username,
                "role": role.value,
                "ver": auth_version,
                "exp": exp,
            }
        ).encode()
    )
    sig = _b64e(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}", exp


def verify_token(token: str, secret: str) -> AuthenticatedUser:
    """驗簽 + 檢查未過期，回傳已驗證身份；失敗則丟 ValueError。"""
    try:
        body, sig = token.split(".", 1)
    except ValueError:
        raise ValueError("token 格式錯誤")

    expected = _b64e(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, expected):
        raise ValueError("簽章驗證失敗")

    payload = json.loads(_b64d(body))
    if payload.get("exp", 0) < time.time():
        raise ValueError("token 已過期")
    try:
        role = UserRole(payload.get("role", UserRole.OPERATOR.value))
        username = str(payload["sub"])
        auth_version = int(payload.get("ver", 1))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("token 身份資料錯誤") from exc
    return AuthenticatedUser(
        username=username,
        role=role,
        auth_version=auth_version,
    )


def check_credentials(username: str, password: str, expected_user: str, expected_pw: str) -> bool:
    """以 compare_digest 做定時安全比對。"""
    return hmac.compare_digest(username, expected_user) and hmac.compare_digest(
        password, expected_pw
    )
