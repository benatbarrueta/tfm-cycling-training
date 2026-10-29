from dataclasses import dataclass
from urllib.parse import urlencode

import httpx


class StravaError(RuntimeError):
    pass


class StravaAuthenticationError(StravaError):
    pass


class StravaRateLimitError(StravaError):
    pass


class StravaUnavailableError(StravaError):
    pass


@dataclass(frozen=True)
class StravaAuthorization:
    athlete_id: str
    athlete_name: str | None
    access_token: str
    refresh_token: str
    expires_at: int
    scopes: list[str]


@dataclass(frozen=True)
class StravaTokens:
    access_token: str
    refresh_token: str
    expires_at: int


class StravaClient:
    authorization_endpoint = "https://www.strava.com/oauth/authorize"
    token_endpoint = "https://www.strava.com/oauth/token"
    deauthorization_endpoint = "https://www.strava.com/oauth/deauthorize"
    api_base_url = "https://www.strava.com/api/v3"

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

    def refresh_access_token(self, refresh_token: str) -> StravaTokens:
        try:
            response = httpx.post(
                self.token_endpoint,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
                timeout=10,
            )
            self._raise_for_status(response)
            data = response.json()
            return StravaTokens(
                access_token=data["access_token"],
                refresh_token=data["refresh_token"],
                expires_at=int(data["expires_at"]),
            )
        except StravaError:
            raise
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise StravaUnavailableError("Strava token could not be refreshed") from exc

    def list_athlete_activities(
        self,
        access_token: str,
        *,
        after: int,
        before: int,
        page: int,
        per_page: int,
    ) -> list[dict]:
        try:
            response = httpx.get(
                f"{self.api_base_url}/athlete/activities",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "after": after,
                    "before": before,
                    "page": page,
                    "per_page": per_page,
                },
                timeout=15,
            )
            self._raise_for_status(response)
            data = response.json()
            if not isinstance(data, list):
                raise StravaUnavailableError("Strava returned an invalid activity list")
            return data
        except StravaError:
            raise
        except (httpx.HTTPError, TypeError, ValueError) as exc:
            raise StravaUnavailableError("Strava activities could not be loaded") from exc

    def get_activity(self, access_token: str, activity_id: str) -> dict:
        try:
            response = httpx.get(
                f"{self.api_base_url}/activities/{activity_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=15,
            )
            self._raise_for_status(response)
            data = response.json()
            if not isinstance(data, dict):
                raise StravaUnavailableError("Strava returned an invalid activity")
            return data
        except StravaError:
            raise
        except (httpx.HTTPError, TypeError, ValueError) as exc:
            raise StravaUnavailableError("Strava activity could not be loaded") from exc

    def get_activity_streams(self, access_token: str, activity_id: str) -> dict[str, list]:
        try:
            response = httpx.get(
                f"{self.api_base_url}/activities/{activity_id}/streams",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "keys": "time,distance,heartrate,watts,cadence,altitude",
                    "key_by_type": "true",
                },
                timeout=20,
            )
            if response.status_code == 404:
                return {}
            self._raise_for_status(response)
            data = response.json()
            if not isinstance(data, dict):
                raise StravaUnavailableError("Strava returned invalid activity streams")
            streams: dict[str, list] = {}
            for key, stream in data.items():
                if isinstance(stream, dict) and isinstance(stream.get("data"), list):
                    streams[str(key)] = stream["data"]
            return streams
        except StravaError:
            raise
        except (httpx.HTTPError, TypeError, ValueError) as exc:
            raise StravaUnavailableError("Strava activity streams could not be loaded") from exc

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

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code == 401:
            raise StravaAuthenticationError("Strava authorization has expired")
        if response.status_code == 429:
            raise StravaRateLimitError("Strava rate limit reached")
        if response.status_code >= 500:
            raise StravaUnavailableError("Strava is temporarily unavailable")
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise StravaError("Strava rejected the request") from exc
