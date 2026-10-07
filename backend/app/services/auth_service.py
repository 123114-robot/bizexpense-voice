import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    UserRead,
)

ALGORITHM = "HS256"
HASH_ITERATIONS = 600_000
DUMMY_HASH = (
    "pbkdf2_sha256$600000$MDAwMDAwMDAwMDAwMDAwMA==$"
    "A6n94D7U5m9gFf9qah7IwnNZYxH4H6NQ3qXv6iRPDH8="
)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt, HASH_ITERATIONS
    )
    return "$".join(
        (
            "pbkdf2_sha256",
            str(HASH_ITERATIONS),
            base64.b64encode(salt).decode(),
            base64.b64encode(digest).decode(),
        )
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_text, digest_text = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_text)
        expected = base64.b64decode(digest_text)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt, int(iterations)
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def _token(self, user: User) -> str:
        expires = datetime.now(timezone.utc) + timedelta(
            minutes=self.settings.access_token_minutes
        )
        return jwt.encode(
            {"sub": str(user.id), "exp": expires, "type": "access"},
            self.settings.jwt_secret,
            algorithm=ALGORITHM,
        )

    @staticmethod
    def _refresh_token_hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def _response(self, user: User) -> AuthResponse:
        raw_refresh_token = secrets.token_urlsafe(48)
        self.db.add(
            RefreshToken(
                user_id=user.id,
                token_hash=self._refresh_token_hash(raw_refresh_token),
                expires_at=datetime.now(timezone.utc)
                + timedelta(days=self.settings.refresh_token_days),
            )
        )
        self.db.commit()
        return AuthResponse(
            access_token=self._token(user),
            refresh_token=raw_refresh_token,
            user=UserRead.model_validate(user),
        )

    def register(self, payload: RegisterRequest) -> AuthResponse:
        email = payload.email.lower()
        existing = self.db.scalar(
            select(User).where(func.lower(User.email) == email)
        )
        if existing:
            raise HTTPException(409, "Email is already registered")
        user = User(
            name=payload.name.strip(),
            email=email,
            password_hash=hash_password(payload.password),
            role="owner",
        )
        self.db.add(user)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(409, "Email is already registered") from exc
        self.db.refresh(user)
        return self._response(user)

    def login(self, payload: LoginRequest) -> AuthResponse:
        user = self.db.scalar(
            select(User).where(func.lower(User.email) == payload.email.lower())
        )
        encoded = user.password_hash if user and user.password_hash else DUMMY_HASH
        if not verify_password(payload.password, encoded) or not user:
            raise HTTPException(401, "Invalid email or password")
        return self._response(user)

    def refresh(self, payload: RefreshTokenRequest) -> AuthResponse:
        token = self.db.scalar(
            select(RefreshToken)
            .where(
                RefreshToken.token_hash
                == self._refresh_token_hash(payload.refresh_token)
            )
            .with_for_update()
        )
        now = datetime.now(timezone.utc)
        expires_at = token.expires_at if token else None
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if not token or token.revoked_at or not expires_at or expires_at <= now:
            raise HTTPException(401, "Invalid or expired refresh token")
        token.revoked_at = now
        return self._response(token.user)

    def logout(self, payload: RefreshTokenRequest) -> None:
        token = self.db.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash
                == self._refresh_token_hash(payload.refresh_token)
            )
        )
        if token and not token.revoked_at:
            token.revoked_at = datetime.now(timezone.utc)
            self.db.commit()

    def user_from_token(self, token: str) -> User:
        try:
            payload = jwt.decode(
                token, self.settings.jwt_secret, algorithms=[ALGORITHM]
            )
            if payload.get("type") not in (None, "access"):
                raise ValueError("Unexpected token type")
            user_id = int(payload["sub"])
        except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
            raise HTTPException(401, "Invalid or expired access token") from exc
        user = self.db.get(User, user_id)
        if not user:
            raise HTTPException(401, "Invalid or expired access token")
        return user
