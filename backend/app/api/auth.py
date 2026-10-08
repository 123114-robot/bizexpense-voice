from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import get_settings
from app.core.rate_limit import RateLimitDependency
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    UserRead,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])
bearer = HTTPBearer(auto_error=False)
settings = get_settings()
auth_rate_limit = RateLimitDependency(
    "auth", settings.auth_rate_limit_requests, settings.rate_limit_window_seconds
)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "Authentication required")
    return AuthService(db).user_from_token(credentials.credentials)


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=201,
    dependencies=[Depends(auth_rate_limit)],
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    return AuthService(db).register(payload)


@router.post(
    "/login", response_model=AuthResponse, dependencies=[Depends(auth_rate_limit)]
)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    return AuthService(db).login(payload)


@router.post(
    "/refresh", response_model=AuthResponse, dependencies=[Depends(auth_rate_limit)]
)
def refresh(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    return AuthService(db).refresh(payload)


@router.post(
    "/logout", status_code=204, dependencies=[Depends(auth_rate_limit)]
)
def logout(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    AuthService(db).logout(payload)


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(current_user)):
    return user
