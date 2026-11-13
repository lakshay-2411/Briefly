import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app import db
from app.auth import User, get_current_user
from app.services import storage

log = logging.getLogger(__name__)

router = APIRouter(prefix="/episodes", tags=["episodes"])


class EpisodeSummary(BaseModel):
    id: UUID
    briefing_id: UUID
    topic: str
    status: str  # researching | writing | synthesizing | scheduled | ready | failed
    title: str | None
    summary: str | None
    duration_seconds: int | None
    error: str | None
    deliver_at: datetime
    created_at: datetime


class Source(BaseModel):
    title: str
    url: str


class EpisodeDetail(EpisodeSummary):
    script: str | None
    sources: list[Source] | None
    audio_url: str | None


SELECT = """
    select e.id, e.briefing_id, b.topic, e.status, e.title, e.summary, e.duration_seconds,
           e.error, e.deliver_at, e.created_at, e.script, e.sources, e.audio_path
    from episodes e join briefings b on b.id = e.briefing_id
"""


def _hold_until_delivery(row: dict) -> dict:
    """An episode generated ahead of time stays hidden until its delivery time."""
    if row["status"] == "ready" and row["deliver_at"] > datetime.now(timezone.utc):
        row.update(status="scheduled", title=None, summary=None, script=None, sources=None, audio_path=None)
    return row


@router.get("", response_model=list[EpisodeSummary])
def list_episodes(briefing_id: UUID | None = None, user: User = Depends(get_current_user)):
    if briefing_id:
        rows = db.fetch_all(
            f"{SELECT} where e.user_id = %s and e.briefing_id = %s order by e.created_at desc",
            (user.id, briefing_id),
        )
    else:
        rows = db.fetch_all(f"{SELECT} where e.user_id = %s order by e.created_at desc limit 100", (user.id,))
    return [_hold_until_delivery(r) for r in rows]


@router.get("/{episode_id}", response_model=EpisodeDetail)
def get_episode(episode_id: UUID, user: User = Depends(get_current_user)):
    row = db.fetch_one(f"{SELECT} where e.id = %s and e.user_id = %s", (episode_id, user.id))
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Episode not found")
    row = _hold_until_delivery(row)
    row["audio_url"] = None
    if row["audio_path"]:
        try:
            row["audio_url"] = storage.signed_url(row["audio_path"])
        except Exception:
            log.exception("Could not sign audio URL for episode %s", episode_id)  # still show the rest
    return row
