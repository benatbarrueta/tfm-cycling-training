import os

os.environ["APP_ENV"] = "test"
os.environ["SESSION_SECRET"] = "test-secret"
os.environ["DATABASE_URL"] = "sqlite:///./test-auth-import.db"

from datetime import timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.auth.google import GoogleIdentity
from app.auth.sessions import hash_token, utc_now
from app.core.config import Settings, get_settings
from app.database.base import Base
from app.database.models import ActivityRecord, CyclistProfile, ExternalConnection, UserSession
from app.database.session import get_db
from app.main import app
from app.api.routes import auth, integrations
from app.integrations.strava import StravaAuthorization


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(engine)


def override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


def override_settings():
    return Settings(
        app_env="development",
        database_url="sqlite://",
        session_secret="test-secret",
        google_client_id="client-id",
        strava_client_id="strava-client",
        strava_client_secret="strava-secret",
        strava_redirect_uri="http://testserver/api/integrations/strava/callback",
        external_token_encryption_key="encryption-secret",
    )


app.dependency_overrides[get_db] = override_db
app.dependency_overrides[get_settings] = override_settings


class FakeVerifier:
    def __init__(self, client_id: str):
        self.client_id = client_id

    def verify(self, credential: str) -> GoogleIdentity:
        if credential == "invalid":
            raise auth.GoogleTokenError("invalid")
        return GoogleIdentity(
            subject="other-subject" if credential == "collision" else "google-subject",
            email="rider@example.com",
            name="Rider",
            picture=None,
            email_verified=True,
        )


auth.GoogleTokenVerifier = FakeVerifier
client = TestClient(app)


def setup_function():
    with TestingSession() as db:
        db.query(UserSession).delete()
        db.query(CyclistProfile).delete()
        db.query(ActivityRecord).delete()
        for table in reversed(Base.metadata.sorted_tables):
            if table.name == "users":
                db.execute(table.delete())
        db.commit()


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_demo_login_me_and_logout():
    login = client.post("/api/auth/demo")
    assert login.status_code == 200
    assert login.json()["is_demo"] is True
    assert client.get("/api/auth/me").json()["email"] == "demo@veloform.local"

    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_strava_connection_requires_personal_account_and_persists_encrypted_tokens(monkeypatch):
    client.post("/api/auth/demo")
    assert client.post("/api/integrations/strava/connect").status_code == 403
    client.cookies.clear()

    client.post("/api/auth/google", json={"credential": "valid"})
    start = client.post("/api/integrations/strava/connect")
    assert start.status_code == 200
    authorization_url = start.json()["authorization_url"]
    assert "activity%3Aread_all" in authorization_url

    from urllib.parse import parse_qs, urlparse

    state_value = parse_qs(urlparse(authorization_url).query)["state"][0]

    monkeypatch.setattr(
        integrations.StravaClient,
        "exchange_code",
        lambda self, code, scopes=None: StravaAuthorization(
            athlete_id="12345",
            athlete_name="Test Rider",
            access_token="plain-access-token",
            refresh_token="plain-refresh-token",
            expires_at=2_000_000_000,
            scopes=["read", "activity:read_all"],
        ),
    )
    callback = client.get(
        "/api/integrations/strava/callback",
        params={"state": state_value, "code": "authorization-code", "scope": "read,activity:read_all"},
        follow_redirects=False,
    )
    assert callback.status_code == 303
    assert "connection=strava-success" in callback.headers["location"]

    listed = client.get("/api/integrations").json()["items"][0]
    assert listed["connected"] is True
    assert listed["external_display_name"] == "Test Rider"
    with TestingSession() as db:
        connection = db.scalar(select(ExternalConnection))
        assert connection is not None
        assert "plain-access-token" not in connection.access_token_encrypted
        assert "plain-refresh-token" not in connection.refresh_token_encrypted

    monkeypatch.setattr(integrations.StravaClient, "deauthorize", lambda self, access_token: None)
    assert client.delete("/api/integrations/strava").status_code == 204
    assert client.get("/api/integrations").json()["items"][0]["connected"] is False


def test_strava_callback_rejects_tampered_state():
    client.post("/api/auth/google", json={"credential": "valid"})
    response = client.get(
        "/api/integrations/strava/callback",
        params={"state": "tampered.state", "code": "authorization-code"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "connection=strava-invalid-state" in response.headers["location"]
    with TestingSession() as db:
        assert db.query(ExternalConnection).count() == 0


def test_demo_cookie_is_http_only_and_session_stores_only_hash():
    response = client.post("/api/auth/demo")
    assert response.cookies.get("veloform_session")
    assert "HttpOnly" in response.headers["set-cookie"]
    raw_token = response.cookies.get("veloform_session")
    with TestingSession() as db:
        record = db.scalar(select(UserSession))
        assert record is not None
        assert record.token_hash == hash_token(raw_token, "test-secret")
        assert record.token_hash != raw_token


def test_google_login_uses_subject_and_rejects_invalid_token():
    response = client.post("/api/auth/google", json={"credential": "valid"})
    assert response.status_code == 200
    assert response.json()["email"] == "rider@example.com"
    assert client.post("/api/auth/google", json={"credential": "invalid"}).status_code == 401


def test_google_identity_collision_returns_conflict():
    client.post("/api/auth/google", json={"credential": "valid"})
    client.cookies.clear()
    assert client.post("/api/auth/google", json={"credential": "collision"}).status_code == 409


def test_demo_login_is_disabled_outside_development():
    app.dependency_overrides[get_settings] = lambda: Settings(
        app_env="production",
        database_url="sqlite://",
        session_secret="test-secret",
        google_client_id="client-id",
    )
    try:
        assert client.post("/api/auth/demo").status_code == 404
    finally:
        app.dependency_overrides[get_settings] = override_settings


def test_expired_session_is_rejected():
    client.post("/api/auth/demo")
    with TestingSession() as db:
        record = db.scalar(select(UserSession))
        assert record is not None
        record.expires_at = utc_now() - timedelta(seconds=1)
        db.commit()

    assert client.get("/api/auth/me").status_code == 401


def test_cyclist_profile_requires_authentication_and_persists_owner_data():
    assert client.get("/api/profile").status_code == 401
    client.post("/api/auth/demo")
    payload = {
        "ftp": 280,
        "weekly_hours": 10,
        "available_days": ["SUNDAY", "TUESDAY", "TUESDAY"],
        "modality": "XCO",
        "level": "ADVANCED",
        "objective": "PERFORMANCE",
        "target_date": None,
        "timezone": "Europe/Madrid",
    }
    assert client.put("/api/profile", json=payload).status_code == 422

    payload["available_days"] = ["SUNDAY", "TUESDAY", "FRIDAY"]
    response = client.put("/api/profile", json=payload)
    assert response.status_code == 200
    assert response.json()["available_days"] == ["TUESDAY", "FRIDAY", "SUNDAY"]
    assert client.get("/api/profile").json()["ftp"] == 280

    with TestingSession() as db:
        assert db.query(CyclistProfile).count() == 1


def test_profile_validates_domain_and_race_date():
    client.post("/api/auth/demo")
    base = {
        "ftp": 250,
        "weekly_hours": 8,
        "available_days": ["TUESDAY"],
        "modality": "XCO",
        "level": "INTERMEDIATE",
        "objective": "RACE",
        "target_date": None,
        "timezone": "Europe/Madrid",
    }
    assert client.put("/api/profile", json=base).status_code == 422
    base["target_date"] = "2030-06-01"
    base["timezone"] = "not/a/timezone"
    assert client.put("/api/profile", json=base).status_code == 422


def test_activity_crud_is_scoped_to_authenticated_user_and_normalizes_time():
    assert client.get("/api/activities").status_code == 401
    client.post("/api/auth/demo")
    payload = {
        "title": "Salida larga",
        "started_at": "2026-10-07T17:30:00+02:00",
        "duration_minutes": 120,
        "distance_km": 55,
        "average_power": 180,
        "normalized_power": 195,
        "average_heart_rate": 145,
        "intensity_factor": 0.78,
        "tss": 72,
        "aerobic_decoupling": -1.2,
        "notes": "Buen ritmo",
    }
    response = client.post("/api/activities", json=payload)
    assert response.status_code == 201
    activity_id = response.json()["id"]
    assert response.json()["source"] == "MANUAL"
    assert response.json()["started_at"].startswith("2026-10-07T15:30:00")

    second = {**payload, "title": "Rodaje corto", "started_at": "2026-10-07T20:00:00+02:00", "duration_minutes": 30}
    assert client.post("/api/activities", json=second).status_code == 201
    listed = client.get("/api/activities?limit=1&offset=0")
    assert listed.json()["total"] == 2
    assert len(listed.json()["items"]) == 1
    assert client.get(f"/api/activities/{activity_id}").status_code == 200
    created_at = response.json()["created_at"]

    updated = {**payload, "title": "Salida actualizada"}
    update_response = client.put(f"/api/activities/{activity_id}", json=updated)
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Salida actualizada"
    assert update_response.json()["created_at"] == created_at
    assert client.delete(f"/api/activities/{activity_id}").status_code == 204
    assert client.get(f"/api/activities/{activity_id}").status_code == 404


def test_activity_validation_and_owner_isolation():
    client.post("/api/auth/demo")
    invalid = {
        "title": " ",
        "started_at": "2026-10-07T17:30:00",
        "duration_minutes": -1,
        "tss": -2,
    }
    assert client.post("/api/activities", json=invalid).status_code == 422
    client.cookies.clear()
    other = client.post("/api/auth/google", json={"credential": "valid"})
    assert other.status_code == 200
    assert client.get("/api/activities").json()["total"] == 0
