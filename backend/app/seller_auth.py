"""Seller bearer keys for the initial API pilot; no public registration."""

import json
import os
import secrets
import hashlib
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import dotenv_values
from fastapi import Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr


COOKIE = "seller_session"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def csrf_token(token: str) -> str:
    return digest("seller-csrf-v1:" + token)


def check_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin and origin != str(request.base_url).rstrip("/"):
        raise HTTPException(403, "Cross-origin request rejected")


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: SecretStr = Field(min_length=1, max_length=512)


def seller_auth(keys: dict[str, str] | None = None, database: Path | None = None):
    if keys is None:
        values = {**dotenv_values(Path(__file__).resolve().parents[2] / ".env"), **os.environ}
        try:
            keys = json.loads(values.get("SELLER_API_KEYS") or "{}")
        except (ValueError, TypeError):
            raise ValueError("SELLER_API_KEYS must be a JSON object mapping secret keys to seller IDs") from None
    if not isinstance(keys, dict) or any(not isinstance(k, str) or not k.strip() or not isinstance(v, str) or not v.strip() for k, v in keys.items()):
        raise ValueError("Seller keys and IDs must be nonempty strings")
    configured = dict(keys)

    def authenticate(request: Request, authorization: str | None = Header(default=None)) -> str:
        if not configured:
            raise HTTPException(503, "Seller access is not configured")
        scheme, _, token = (authorization or "").partition(" ")
        if scheme.lower() == "bearer":
            for key, seller in configured.items():
                if secrets.compare_digest(token.encode(), key.encode()):
                    return seller
        if not authorization and database is not None:
            token = request.cookies.get(COOKIE, "")
            with closing(sqlite3.connect(database)) as connection:
                row = connection.execute("SELECT seller_id, key_hash, expires_at FROM seller_sessions WHERE token_hash=?", (digest(token),)).fetchone()
            if row and row[2] > datetime.now(timezone.utc).isoformat() and any(
                seller == row[0] and secrets.compare_digest(digest(key), row[1]) for key, seller in configured.items()
            ):
                if request.method not in {"GET", "HEAD", "OPTIONS"}:
                    check_origin(request)
                    if not secrets.compare_digest(request.headers.get("x-csrf-token", "").encode(), csrf_token(token).encode()):
                        raise HTTPException(403, "Session security check failed. Reload and retry.")
                return row[0]
        raise HTTPException(401, "Seller authentication required", headers={"WWW-Authenticate": "Bearer"})

    return authenticate


def mount_sessions(application, database: Path, authenticate) -> None:
    @application.post("/session")
    def login(body: Login, request: Request, response: Response):
        check_origin(request)
        if request.headers.get("x-requested-with") != "checkout-app":
            raise HTTPException(403, "Login must originate from the seller app")
        key = body.key.get_secret_value()
        seller = authenticate(request, "Bearer " + key)
        token = secrets.token_urlsafe(32)
        expiry = (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat()
        with closing(sqlite3.connect(database)) as connection, connection:
            connection.execute("DELETE FROM seller_sessions WHERE expires_at<=? OR token_hash=?",
                               (datetime.now(timezone.utc).isoformat(), digest(request.cookies.get(COOKIE, ""))))
            connection.execute("INSERT INTO seller_sessions VALUES (?, ?, ?, ?)", (digest(token), seller, digest(key), expiry))
        response.set_cookie(COOKIE, token, httponly=True, secure=request.url.scheme == "https", samesite="strict", max_age=8 * 3600, path="/")
        return {"seller_id": seller, "csrf_token": csrf_token(token)}

    @application.get("/session")
    def session(request: Request, seller: str = Depends(authenticate)):
        return {"seller_id": seller, "csrf_token": csrf_token(request.cookies.get(COOKIE, ""))}

    @application.delete("/session", status_code=204)
    def logout(request: Request, seller: str = Depends(authenticate)):
        with closing(sqlite3.connect(database)) as connection, connection:
            connection.execute("DELETE FROM seller_sessions WHERE token_hash=?", (digest(request.cookies.get(COOKIE, "")),))
        response = Response(status_code=204)
        response.delete_cookie(COOKIE, path="/", httponly=True, samesite="strict", secure=request.url.scheme == "https")
        return response
