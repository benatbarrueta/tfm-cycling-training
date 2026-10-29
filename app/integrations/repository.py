from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import ExternalConnection
from app.integrations.crypto import TokenCipher
from app.integrations.strava import StravaAuthorization


def get_connection(db: Session, user_id: UUID, provider: str) -> ExternalConnection | None:
    return db.scalar(
        select(ExternalConnection).where(
            ExternalConnection.user_id == user_id,
            ExternalConnection.provider == provider,
        )
    )


def save_strava_connection(
    db: Session,
    user_id: UUID,
    authorization: StravaAuthorization,
    cipher: TokenCipher,
) -> ExternalConnection:
    connection = get_connection(db, user_id, "STRAVA")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if connection is None:
        connection = ExternalConnection(user_id=user_id, provider="STRAVA")
        db.add(connection)
    connection.external_user_id = authorization.athlete_id
    connection.external_display_name = authorization.athlete_name
    connection.access_token_encrypted = cipher.encrypt(authorization.access_token)
    connection.refresh_token_encrypted = cipher.encrypt(authorization.refresh_token)
    connection.token_expires_at = datetime.fromtimestamp(authorization.expires_at, timezone.utc).replace(tzinfo=None)
    connection.granted_scopes = authorization.scopes
    connection.status = "CONNECTED"
    connection.connected_at = now
    db.commit()
    db.refresh(connection)
    return connection


def delete_connection(db: Session, connection: ExternalConnection) -> None:
    db.delete(connection)
    db.commit()
