from dataclasses import dataclass
from urllib.parse import urlencode

import httpx


class StravaError(RuntimeError):
    pass


@dataclass(frozen=True)
class StravaAuthorization:
    athlete_id: str
    athlete_name: str | None
    access_token: str
    refresh_token: str
    expires_at: int
    scopes: list[str]


class StravaClient:
    authorization_endpoint = "https://www.strava.com/oauth/authorize"
    token_endpoint = "https://www.strava.com/oauth/token"
    deauthorization_endpoint = "https://www.strava.com/oauth/deauthorize"

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def authorization_url(self, state: str) -> str:
        query = urlencode(
            {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "response_type": "code",
                "approval_prompt": "auto",
                "scope": "read,activity:read_all",
                "state": state,
            }
        )
        return f"{self.authorization_endpoint}?{query}"

    def exchange_code(self, code: str, scopes: str | None = None) -> StravaAuthorization:
        try:
            response = httpx.post(
                self.token_endpoint,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            athlete = data["athlete"]
            name = " ".join(
                part for part in [athlete.get("firstname"), athlete.get("lastname")] if part
            ).strip() or athlete.get("username")
            granted = [item for item in (scopes or "").replace(" ", ",").split(",") if item]
            return StravaAuthorization(
                athlete_id=str(athlete["id"]),
                athlete_name=name,
                access_token=data["access_token"],
                refresh_token=data["refresh_token"],
                expires_at=int(data["expires_at"]),
                scopes=granted,
            )
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise StravaError("Strava authorization could not be completed") from exc

    def deauthorize(self, access_token: str) -> None:
        try:
            response = httpx.post(
                self.deauthorization_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise StravaError("Strava connection could not be revoked") from exc
