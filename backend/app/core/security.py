"""極簡簽章 token，僅用標準庫（不引入 JWT 相依）。

適用本機單人研究情境：帳密由設定/環境變數提供，登入後簽發 HMAC-SHA256 token，
之後每個請求帶 `Authorization: Bearer <token>`。這不是企業級 IdP，但比明碼傳遞
或無保護要好，且無外部相依、Docker 映像不變胖。
"""

import base64
import hashlib
import hmac
import json
import time


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def create_token(username: str, secret: str, ttl_seconds: int) -> tuple[str, int]:
    """回傳 (token, expiresAtEpoch)。"""
    exp = int(time.time()) + ttl_seconds
    body = _b64e(json.dumps({"sub": username, "exp": exp}).encode())
    sig = _b64e(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}", exp


def verify_token(token: str, secret: str) -> str:
    """驗簽 + 檢查未過期，回傳 username；失敗則丟 ValueError。"""
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
    return payload["sub"]


def check_credentials(username: str, password: str, expected_user: str, expected_pw: str) -> bool:
    """以 compare_digest 做定時安全比對。"""
    return hmac.compare_digest(username, expected_user) and hmac.compare_digest(
        password, expected_pw
    )
