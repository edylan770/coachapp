from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import security
from app.config import get_settings
from app.db import get_db
from app.deps import CurrentUser
from app.models.user import RefreshToken, User, UserRole
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[Session, Depends(get_db)]


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _issue_token_pair(db: Session, user: User) -> TokenPair:
    """Creates a refresh token row and commits the session (including any
    pending changes, e.g. revocation of the token being rotated)."""
    settings = get_settings()
    raw_refresh = security.generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=security.hash_refresh_token(raw_refresh),
            expires_at=datetime.now(UTC)
            + timedelta(days=settings.refresh_token_ttl_days),
        )
    )
    db.commit()
    return TokenPair(
        access_token=security.create_access_token(user.id, user.role.value),
        refresh_token=raw_refresh,
        expires_in=settings.access_token_ttl_minutes * 60,
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DbSession) -> User:
    # Public signup is trainer-only by design: clients are invited by their
    # trainer (Phase 1), never self-registered.
    user = User(
        email=_normalize_email(payload.email),
        password_hash=security.hash_password(payload.password),
        role=UserRole.trainer,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from None
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, db: DbSession) -> TokenPair:
    user = db.scalar(select(User).where(User.email == _normalize_email(payload.email)))
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
    )
    if (
        user is None
        or user.password_hash is None
        or not security.verify_password(payload.password, user.password_hash)
        or not user.is_active
    ):
        raise invalid
    return _issue_token_pair(db, user)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: DbSession) -> TokenPair:
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
    )
    now = datetime.now(UTC)
    token = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == security.hash_refresh_token(payload.refresh_token)
        )
    )
    if token is None:
        raise invalid
    if token.revoked_at is not None:
        # Reuse of a rotated token — treat as theft and revoke everything active.
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == token.user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        db.commit()
        raise invalid
    if token.expires_at <= now:
        raise invalid
    user = db.get(User, token.user_id)
    if user is None or not user.is_active:
        raise invalid
    token.revoked_at = now  # rotate: committed together with the new token below
    return _issue_token_pair(db, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshRequest, db: DbSession) -> Response:
    """Revokes the given refresh token. Idempotent — unknown or already-revoked
    tokens still return 204. Access tokens simply expire (no blocklist)."""
    token = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == security.hash_refresh_token(payload.refresh_token)
        )
    )
    if token is not None and token.revoked_at is None:
        token.revoked_at = datetime.now(UTC)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserOut)
def me(current_user: CurrentUser) -> User:
    return current_user
