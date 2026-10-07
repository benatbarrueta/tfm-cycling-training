from uuid import UUID

from pydantic import BaseModel, ConfigDict


class GoogleCredential(BaseModel):
    credential: str


class PublicUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    display_name: str
    avatar_url: str | None
    email_verified: bool
    is_demo: bool
