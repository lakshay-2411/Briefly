"""Verify Supabase access tokens (JWTs) sent by the frontend."""

from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

# New Supabase projects sign tokens with asymmetric keys published at this JWKS URL;
# legacy projects use a shared HS256 secret (SUPABASE_JWT_SECRET).
_jwks = jwt.PyJWKClient(f"{settings.supabase_url}/auth/v1/.well-known/jwks.json", cache_keys=True)
_bearer = HTTPBearer(auto_error=False)


@dataclass
class User:
    id: str
    email: str


def _decode(token: str) -> dict:
    if settings.supabase_jwt_secret:
        return jwt.decode(token, settings.supabase_jwt_secret, algorithms=["HS256"], audience="authenticated")
    key = _jwks.get_signing_key_from_jwt(token)
    return jwt.decode(token, key, algorithms=["ES256", "RS256"], audience="authenticated")


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        claims = _decode(creds.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    return User(id=claims["sub"], email=claims.get("email", ""))
