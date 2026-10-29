import base64
import hashlib
import hmac
import json
import secrets
import time
from uuid import UUID


def create_oauth_state(user_id: UUID, secret: str) -> str:
    payload = {
        "user_id": str(user_id),
        "issued_at": int(time.time()),
        "nonce": secrets.token_urlsafe(16),
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).decode("ascii").rstrip("=")
    signature = hmac.new(secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def validate_oauth_state(state: str, user_id: UUID, secret: str, max_age_seconds: int = 600) -> bool:
    try:
        encoded, signature = state.split(".", 1)
        expected = hmac.new(secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return False
        padded = encoded + "=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
        age = int(time.time()) - int(payload["issued_at"])
        return payload["user_id"] == str(user_id) and 0 <= age <= max_age_seconds
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return False
