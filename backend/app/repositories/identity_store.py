from __future__ import annotations

import hashlib
import hmac
import os
import re
import threading
from contextlib import contextmanager
from datetime import UTC, datetime
from functools import lru_cache

import psycopg
from psycopg import sql
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row

from app.core.config import get_settings
from app.core.security import UserRole

_USERNAME = re.compile(r"^[a-z0-9][a-z0-9._-]{2,39}$")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_STRONG_PASSWORD = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{12,72}$"
)
_ITERATIONS = 600_000


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _hash(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        _ITERATIONS,
    ).hex()


class IdentityStore:
    """Persistent PLC identities, pending applications and immutable audit events."""

    def __init__(
        self,
        database_url: str,
        *,
        bootstrap: dict[str, tuple[UserRole, str]],
        schema: str = "plc_identity",
    ) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", schema):
            raise ValueError("invalid PostgreSQL schema")
        self.schema = schema
        self._lock = threading.Lock()
        self._conn = psycopg.connect(
            database_url,
            autocommit=True,
            row_factory=dict_row,
        )
        self._conn.execute(
            sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema))
        )
        self._conn.execute(
            sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema))
        )
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS identities (
                    username TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    role TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    iterations INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    auth_version INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    approved_by TEXT,
                    approved_at TEXT,
                    rejected_by TEXT,
                    rejected_at TEXT
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS identity_audit (
                    id BIGSERIAL PRIMARY KEY,
                    subject TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    source_address TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            self._conn.execute(
                """
                CREATE OR REPLACE FUNCTION prevent_identity_audit_mutation()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                  RAISE EXCEPTION 'identity_audit is append-only'
                    USING ERRCODE = '55000';
                END;
                $$
                """
            )
            self._conn.execute(
                "DROP TRIGGER IF EXISTS identity_audit_append_only ON identity_audit"
            )
            self._conn.execute(
                """
                CREATE TRIGGER identity_audit_append_only
                BEFORE UPDATE OR DELETE ON identity_audit
                FOR EACH ROW EXECUTE FUNCTION prevent_identity_audit_mutation()
                """
            )
        with self._txn() as connection:
            for username, (role, password) in bootstrap.items():
                existing = connection.execute(
                    "SELECT * FROM identities WHERE username = %s",
                    (username,),
                ).fetchone()
                if existing:
                    candidate = _hash(password, bytes.fromhex(existing["salt"]))
                    if (
                        existing["status"] == "ACTIVE"
                        and existing["approved_by"] == "SYSTEM_BOOTSTRAP"
                        and not hmac.compare_digest(candidate, existing["password_hash"])
                    ):
                        salt = os.urandom(16)
                        connection.execute(
                            """
                            UPDATE identities
                            SET password_hash = %s, salt = %s, iterations = %s,
                                auth_version = auth_version + 1
                            WHERE username = %s
                            """,
                            (_hash(password, salt), salt.hex(), _ITERATIONS, username),
                        )
                    continue
                salt = os.urandom(16)
                connection.execute(
                    """
                    INSERT INTO identities (
                        username, display_name, email, role, password_hash, salt,
                        iterations, status, auth_version, created_at, approved_by,
                        approved_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'ACTIVE', 1, %s, 'SYSTEM_BOOTSTRAP', %s)
                    """,
                    (
                        username,
                        role.value,
                        f"{username}@plc.local",
                        role.value,
                        _hash(password, salt),
                        salt.hex(),
                        _ITERATIONS,
                        _now(),
                        _now(),
                    ),
                )

    @contextmanager
    def _txn(self):
        with self._lock:
            with self._conn.transaction():
                self._conn.execute(
                    "SELECT pg_advisory_xact_lock(hashtext(%s))",
                    (self.schema,),
                )
                yield self._conn

    @staticmethod
    def _public(row: dict) -> dict[str, object]:
        return {
            "username": row["username"],
            "name": row["display_name"],
            "email": row["email"],
            "role": row["role"],
            "status": row["status"],
            "authVersion": row["auth_version"],
            "createdAt": row["created_at"],
            "approvedBy": row["approved_by"],
            "approvedAt": row["approved_at"],
            "rejectedBy": row["rejected_by"],
            "rejectedAt": row["rejected_at"],
        }

    @staticmethod
    def _normalize_username(username: str) -> str:
        return (username or "").strip().lower()

    @staticmethod
    def _validate_password(password: str) -> None:
        if not _STRONG_PASSWORD.fullmatch(password or ""):
            raise ValueError("密碼需 12–72 碼，並包含大小寫、數字與符號")

    def register(
        self,
        *,
        username: str,
        name: str,
        email: str,
        role: UserRole,
        password: str,
        source_address: str,
    ) -> dict[str, object]:
        normalized = self._normalize_username(username)
        display_name = (name or "").strip()
        normalized_email = (email or "").strip().lower()
        if not _USERNAME.fullmatch(normalized):
            raise ValueError("帳號格式不正確，請使用 3–40 碼小寫英數字、點、底線或連字號")
        if len(display_name) < 2 or len(display_name) > 120:
            raise ValueError("姓名長度需為 2–120 字元")
        if not _EMAIL.fullmatch(normalized_email):
            raise ValueError("信箱格式不正確")
        self._validate_password(password)
        salt = os.urandom(16)
        created_at = _now()
        try:
            with self._txn() as connection:
                connection.execute(
                    """
                    INSERT INTO identities (
                        username, display_name, email, role, password_hash, salt,
                        iterations, status, auth_version, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'PENDING', 1, %s)
                    """,
                    (
                        normalized,
                        display_name,
                        normalized_email,
                        role.value,
                        _hash(password, salt),
                        salt.hex(),
                        _ITERATIONS,
                        created_at,
                    ),
                )
                self._audit(
                    connection,
                    normalized,
                    "REGISTER",
                    "PENDING",
                    normalized,
                    source_address,
                    f"PLC/{role.value}",
                )
                row = connection.execute(
                    "SELECT * FROM identities WHERE username = %s",
                    (normalized,),
                ).fetchone()
        except UniqueViolation as exc:
            raise ValueError("帳號或信箱已存在") from exc
        return self._public(row)

    def verify(self, username: str, password: str) -> dict[str, object] | None:
        normalized = self._normalize_username(username)
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM identities WHERE username = %s",
                (normalized,),
            ).fetchone()
        if not row or row["status"] != "ACTIVE":
            return None
        candidate = _hash(password, bytes.fromhex(row["salt"]))
        if not hmac.compare_digest(candidate, row["password_hash"]):
            return None
        return self._public(row)

    def get_active(self, username: str) -> dict[str, object] | None:
        normalized = self._normalize_username(username)
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM identities WHERE username = %s AND status = 'ACTIVE'",
                (normalized,),
            ).fetchone()
        return self._public(row) if row else None

    def pending(self) -> list[dict[str, object]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM identities WHERE status = 'PENDING' ORDER BY created_at"
            ).fetchall()
        return [self._public(row) for row in rows]

    def decide(
        self,
        username: str,
        *,
        approve: bool,
        actor: str,
        source_address: str,
    ) -> dict[str, object]:
        normalized = self._normalize_username(username)
        normalized_actor = self._normalize_username(actor)
        if normalized == normalized_actor:
            raise ValueError("不得核准自己的帳號申請")
        status = "ACTIVE" if approve else "REJECTED"
        actor_column = "approved_by" if approve else "rejected_by"
        time_column = "approved_at" if approve else "rejected_at"
        with self._txn() as connection:
            reviewer = connection.execute(
                """
                SELECT role, status FROM identities
                WHERE username = %s
                """,
                (normalized_actor,),
            ).fetchone()
            if (
                not reviewer
                or reviewer["status"] != "ACTIVE"
                or reviewer["role"] != UserRole.LEAD.value
            ):
                raise ValueError("帳號申請只能由有效的 PLC Lead 審核")
            row = connection.execute(
                "SELECT * FROM identities WHERE username = %s",
                (normalized,),
            ).fetchone()
            if not row:
                raise ValueError("申請不存在")
            if row["status"] != "PENDING":
                raise ValueError("帳號目前不是待核准狀態")
            connection.execute(
                f"""
                UPDATE identities
                SET status = %s, {actor_column} = %s, {time_column} = %s,
                    auth_version = auth_version + 1
                WHERE username = %s
                """,
                (status, normalized_actor, _now(), normalized),
            )
            self._audit(
                connection,
                normalized,
                "ACCOUNT_APPROVAL",
                status,
                normalized_actor,
                source_address,
                f"{status} by {normalized_actor}",
            )
            updated = connection.execute(
                "SELECT * FROM identities WHERE username = %s",
                (normalized,),
            ).fetchone()
        return self._public(updated)

    def audit(self, limit: int = 100) -> list[dict[str, object]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT subject, event_type, outcome, actor, source_address,
                       detail, created_at
                FROM identity_audit ORDER BY id DESC LIMIT %s
                """,
                (max(1, min(limit, 500)),),
            ).fetchall()
        return [
            {
                "subject": row["subject"],
                "eventType": row["event_type"],
                "outcome": row["outcome"],
                "actor": row["actor"],
                "sourceAddress": row["source_address"],
                "detail": row["detail"],
                "createdAt": row["created_at"],
            }
            for row in rows
        ]

    @staticmethod
    def _audit(
        connection: psycopg.Connection,
        subject: str,
        event_type: str,
        outcome: str,
        actor: str,
        source_address: str,
        detail: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO identity_audit (
                subject, event_type, outcome, actor, source_address, detail,
                created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                subject,
                event_type,
                outcome,
                actor,
                source_address[:96],
                detail[:500],
                _now(),
            ),
        )


@lru_cache
def get_identity_store() -> IdentityStore:
    settings = get_settings()
    bootstrap = {
        settings.auth_username: (UserRole.OPERATOR, settings.auth_password),
        settings.auth_engineer_username: (UserRole.ENGINEER, settings.auth_password),
        settings.auth_lead_username: (UserRole.LEAD, settings.auth_password),
    }
    return IdentityStore(
        settings.database_url,
        bootstrap=bootstrap,
        schema=settings.database_schema,
    )
