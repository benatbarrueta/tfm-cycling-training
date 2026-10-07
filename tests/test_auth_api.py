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
from app.database.models import UserSession
from app.database.session import get_db
from app.main import app
from app.api.routes import auth


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
