from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.google import GoogleIdentity
from app.database.models import User


class IdentityConflictError(ValueError):
    pass


def get_by_google_subject(db: Session, subject: str) -> User | None:
    return db.scalar(select(User).where(User.google_subject == subject))


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def upsert_google_user(db: Session, identity: GoogleIdentity) -> User:
    user = get_by_google_subject(db, identity.subject)
    if user is None:
        email_user = get_by_email(db, identity.email)
        if email_user is not None and email_user.google_subject != identity.subject:
            raise IdentityConflictError("Google identity conflicts with an existing user")
        user = User(
            google_subject=identity.subject,
            email=identity.email,
            display_name=identity.name,
            avatar_url=identity.picture,
            email_verified=identity.email_verified,
            is_demo=False,
        )
        db.add(user)
    else:
        user.email = identity.email
        user.display_name = identity.name
        user.avatar_url = identity.picture
        user.email_verified = identity.email_verified
    user.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(user)
    return user


def get_or_create_demo_user(db: Session) -> User:
    user = get_by_email(db, "demo@veloform.local")
    if user is None:
        user = User(
            email="demo@veloform.local",
            display_name="Ciclista Demo",
            email_verified=True,
            is_demo=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
