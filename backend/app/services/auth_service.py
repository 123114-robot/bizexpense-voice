import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserRead

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
            {"sub": str(user.id), "exp": expires},
            self.settings.jwt_secret,
            algorithm=ALGORITHM,
        )

    def _response(self, user: User) -> AuthResponse:
        return AuthResponse(access_token=self._token(user), user=UserRead.model_validate(user))

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

    def user_from_token(self, token: str) -> User:
        try:
            payload = jwt.decode(
                token, self.settings.jwt_secret, algorithms=[ALGORITHM]
            )
            user_id = int(payload["sub"])
        except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
            raise HTTPException(401, "Invalid or expired access token") from exc
        user = self.db.get(User, user_id)
        if not user:
            raise HTTPException(401, "Invalid or expired access token")
        return user
