import threading
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx

from app.config import get_settings
from app.db.repo import get_conn

ACCEPT = "application/vnd.allegro.public.v1+json"
CONTENT = "application/vnd.allegro.public.v1+json"

# Scopes required for the seller half (offer create/reprice, fee preview, profile).
USER_SCOPES = [
    "allegro:api:sale:offers:read",
    "allegro:api:sale:offers:write",
    "allegro:api:billing:read",
    "allegro:api:sale:settings:read",
    "allegro:api:profile:read",
]


class AllegroError(RuntimeError):
    pass


class NotAuthorized(AllegroError):
    """Raised when no valid seller (authorization_code) token is available."""


class _RateLimiter:
    """Token bucket. Allegro allows ~9000 req/min; we stay well under that."""

    def __init__(self, rate_per_sec: float = 100.0, capacity: float = 100.0):
        self.rate = rate_per_sec
        self.capacity = capacity
        self.tokens = capacity
        self.updated = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        with self._lock:
            now = time.monotonic()
            self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.rate)
            self.updated = now
            if self.tokens < 1:
                sleep_for = (1 - self.tokens) / self.rate
                time.sleep(sleep_for)
                self.tokens = 0
            else:
                self.tokens -= 1


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _save_token(grant_type, scope_set, access_token, refresh_token, expires_in) -> None:
    expires_at = (_now() + timedelta(seconds=int(expires_in) - 60)).isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO oauth_tokens(grant_type, scope_set, access_token, refresh_token, expires_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, datetime('now')) "
            "ON CONFLICT(grant_type) DO UPDATE SET "
            "scope_set=excluded.scope_set, access_token=excluded.access_token, "
            "refresh_token=excluded.refresh_token, expires_at=excluded.expires_at, "
            "updated_at=datetime('now')",
            (grant_type, scope_set, access_token, refresh_token, expires_at),
        )


def _load_token(grant_type):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM oauth_tokens WHERE grant_type = ?", (grant_type,)
        ).fetchone()
    return dict(row) if row else None


class AllegroClient:
    def __init__(self, settings=None):
        self.s = settings or get_settings()
        self._limiter = _RateLimiter()
        self._http = httpx.Client(timeout=30.0)

    # ---- OAuth ---------------------------------------------------------------
    def _basic_auth(self) -> tuple[str, str]:
        return (self.s.allegro_client_id, self.s.allegro_client_secret)

    def _token_request(self, data: dict) -> dict:
        resp = self._http.post(
            f"{self.s.auth_base}/token",
            data=data,
            auth=self._basic_auth(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if resp.status_code != 200:
            raise AllegroError(f"token request failed: {resp.status_code} {resp.text}")
        return resp.json()

    def get_public_token(self) -> str:
        tok = _load_token("client_credentials")
        if tok and datetime.fromisoformat(tok["expires_at"]) > _now():
            return tok["access_token"]
        data = self._token_request({"grant_type": "client_credentials"})
        _save_token("client_credentials", None, data["access_token"], None, data["expires_in"])
        return data["access_token"]

    def authorize_url(self, state: str = "") -> str:
        params = {
            "response_type": "code",
            "client_id": self.s.allegro_client_id,
            "redirect_uri": self.s.allegro_redirect_uri,
            "scope": " ".join(USER_SCOPES),
        }
        if state:
            params["state"] = state
        return f"{self.s.auth_base}/authorize?{urlencode(params)}"

    def exchange_code(self, code: str) -> None:
        data = self._token_request({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.s.allegro_redirect_uri,
        })
        _save_token("authorization_code", " ".join(USER_SCOPES),
                    data["access_token"], data.get("refresh_token"), data["expires_in"])

    def get_user_token(self) -> str:
        tok = _load_token("authorization_code")
        if not tok:
            raise NotAuthorized("seller account not connected — visit /auth/connect")
        if datetime.fromisoformat(tok["expires_at"]) > _now():
            return tok["access_token"]
        if not tok["refresh_token"]:
            raise NotAuthorized("no refresh token — reconnect the seller account")
        data = self._token_request({
            "grant_type": "refresh_token",
            "refresh_token": tok["refresh_token"],
            "redirect_uri": self.s.allegro_redirect_uri,
        })
        # Refresh tokens are single-use: persist the rotated one.
        _save_token("authorization_code", tok["scope_set"],
                    data["access_token"], data.get("refresh_token", tok["refresh_token"]),
                    data["expires_in"])
        return data["access_token"]

    def has_seller_token(self) -> bool:
        return _load_token("authorization_code") is not None

    # ---- HTTP ----------------------------------------------------------------
    def request(self, method: str, path: str, *, user: bool = False, **kwargs) -> dict:
        token = self.get_user_token() if user else self.get_public_token()
        headers = kwargs.pop("headers", {})
        headers.setdefault("Accept", ACCEPT)
        headers["Authorization"] = f"Bearer {token}"
        if method in ("POST", "PUT", "PATCH") and "json" in kwargs:
            headers.setdefault("Content-Type", CONTENT)

        url = f"{self.s.api_base}{path}"
        for attempt in range(5):
            self._limiter.acquire()
            resp = self._http.request(method, url, headers=headers, **kwargs)
            if resp.status_code == 429:
                wait = float(resp.headers.get("Retry-After", 2 ** attempt))
                time.sleep(wait)
                continue
            if resp.status_code >= 400:
                raise AllegroError(f"{method} {path} -> {resp.status_code}: {resp.text}")
            return resp.json() if resp.content else {}
        raise AllegroError(f"{method} {path} rate-limited after retries")

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)

    def patch(self, path, **kwargs):
        return self.request("PATCH", path, **kwargs)

    def close(self):
        self._http.close()
