from dataclasses import dataclass
from typing import Any, Protocol

from google.auth.transport import requests
from google.oauth2 import id_token


class GoogleTokenError(ValueError):
    pass


@dataclass(frozen=True)
class GoogleIdentity:
    subject: str
    email: str
    name: str
    picture: str | None
    email_verified: bool


class GoogleVerifier(Protocol):
    def verify(self, credential: str) -> GoogleIdentity: ...


class GoogleTokenVerifier:
    def __init__(self, client_id: str):
        self.client_id = client_id

    def verify(self, credential: str) -> GoogleIdentity:
        if not self.client_id:
            raise GoogleTokenError("Google authentication is not configured")
        try:
            claims: dict[str, Any] = id_token.verify_oauth2_token(
                credential,
                requests.Request(),
                self.client_id,
            )
        except Exception as exc:
            raise GoogleTokenError("Invalid Google credential") from exc

        if claims.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
            raise GoogleTokenError("Invalid Google issuer")
        if not claims.get("sub") or not claims.get("email"):
            raise GoogleTokenError("Google identity is incomplete")
        if claims.get("email_verified") is not True:
            raise GoogleTokenError("Google email is not verified")

        return GoogleIdentity(
            subject=str(claims["sub"]),
            email=str(claims["email"]),
            name=str(claims.get("name") or claims["email"]),
            picture=claims.get("picture"),
            email_verified=True,
        )
