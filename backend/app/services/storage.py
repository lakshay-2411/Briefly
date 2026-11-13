"""Supabase Storage (private bucket) via its REST API."""

import httpx

from app.config import settings

BUCKET = "episodes"


def _headers() -> dict:
    return {"apikey": settings.supabase_service_role_key}


def upload_mp3(path: str, data: bytes) -> None:
    resp = httpx.post(
        f"{settings.supabase_url}/storage/v1/object/{BUCKET}/{path}",
        headers={**_headers(), "Content-Type": "audio/mpeg", "x-upsert": "true"},
        content=data,
        timeout=120.0,
    )
    resp.raise_for_status()


def signed_url(path: str, expires_in: int = 3600) -> str:
    resp = httpx.post(
        f"{settings.supabase_url}/storage/v1/object/sign/{BUCKET}/{path}",
        headers=_headers(),
        json={"expiresIn": expires_in},
        timeout=30.0,
    )
    resp.raise_for_status()
    return f"{settings.supabase_url}/storage/v1{resp.json()['signedURL']}"
