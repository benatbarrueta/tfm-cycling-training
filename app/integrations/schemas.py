from datetime import datetime

from pydantic import BaseModel


class ExternalConnectionRead(BaseModel):
    provider: str
    configured: bool
    connected: bool
    status: str | None = None
    external_display_name: str | None = None
    connected_at: datetime | None = None
    last_sync_at: datetime | None = None


class IntegrationList(BaseModel):
    items: list[ExternalConnectionRead]


class ConnectResponse(BaseModel):
    authorization_url: str
