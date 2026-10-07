from datetime import datetime, timedelta, timezone
from hashlib import sha256
import hmac
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.models import User, UserSession


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hash_token(token: str, secret: str = "") -> str:
    return hmac.new(
        secret.encode("utf-8"),
        token.encode("utf-8"),
        sha256,
    ).hexdigest()


def create_session(db: Session, user: User, settings: Settings) -> str:
    token = secrets.token_urlsafe(32)
    record = UserSession(
        user_id=user.id,
        token_hash=hash_token(token, settings.session_secret),
        expires_at=utc_now() + timedelta(days=settings.session_ttl_days),
    )
    db.add(record)
    db.commit()
    return token


def get_session_user(db: Session, token: str | None, secret: str = "") -> User | None:
    if not token:
        return None
    record = db.scalar(
        select(UserSession).where(UserSession.token_hash == hash_token(token, secret))
    )
    if record is None or record.revoked_at is not None or record.expires_at <= utc_now():
        return None
    return record.user


def revoke_session(db: Session, token: str | None, secret: str = "") -> None:
    if not token:
        return
    record = db.scalar(
        select(UserSession).where(UserSession.token_hash == hash_token(token, secret))
    )
    if record is not None and record.revoked_at is None:
        record.revoked_at = utc_now()
        db.commit()
