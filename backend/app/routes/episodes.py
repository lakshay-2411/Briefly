from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app import db
from app.auth import User, get_current_user
from app.services import storage

router = APIRouter(prefix="/episodes", tags=["episodes"])


class EpisodeSummary(BaseModel):
    id: UUID
    briefing_id: UUID
    topic: str
    status: str
    title: str | None
    summary: str | None
    duration_seconds: int | None
    error: str | None
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
           e.error, e.created_at, e.script, e.sources, e.audio_path
    from episodes e join briefings b on b.id = e.briefing_id
"""


@router.get("", response_model=list[EpisodeSummary])
def list_episodes(briefing_id: UUID | None = None, user: User = Depends(get_current_user)):
    if briefing_id:
        return db.fetch_all(
            f"{SELECT} where e.user_id = %s and e.briefing_id = %s order by e.created_at desc",
            (user.id, briefing_id),
        )
    return db.fetch_all(f"{SELECT} where e.user_id = %s order by e.created_at desc limit 100", (user.id,))


@router.get("/{episode_id}", response_model=EpisodeDetail)
def get_episode(episode_id: UUID, user: User = Depends(get_current_user)):
    row = db.fetch_one(f"{SELECT} where e.id = %s and e.user_id = %s", (episode_id, user.id))
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Episode not found")
    row["audio_url"] = storage.signed_url(row["audio_path"]) if row["audio_path"] else None
    return row
