from datetime import datetime, time
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import AfterValidator, BaseModel, Field

from app import db, pipeline
from app.auth import User, get_current_user
from app.timeutil import next_run_at

router = APIRouter(prefix="/briefings", tags=["briefings"])

COLUMNS = "id, topic, time_of_day, timezone, is_active, next_run_at, created_at"


def _check_tz(tz: str) -> str:
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError(f"Unknown timezone: {tz}")
    return tz


Timezone = Annotated[str, AfterValidator(_check_tz)]


class BriefingIn(BaseModel):
    topic: str = Field(min_length=3, max_length=500)
    time_of_day: time
    timezone: Timezone


class BriefingPatch(BaseModel):
    topic: str | None = Field(default=None, min_length=3, max_length=500)
    time_of_day: time | None = None
    timezone: Timezone | None = None
    is_active: bool | None = None


class BriefingOut(BaseModel):
    id: UUID
    topic: str
    time_of_day: time
    timezone: str
    is_active: bool
    next_run_at: datetime
    created_at: datetime


def _get_owned(briefing_id: UUID, user: User) -> dict:
    row = db.fetch_one(
        f"select {COLUMNS} from briefings where id = %s and user_id = %s", (briefing_id, user.id)
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Briefing not found")
    return row


@router.get("", response_model=list[BriefingOut])
def list_briefings(user: User = Depends(get_current_user)):
    return db.fetch_all(
        f"select {COLUMNS} from briefings where user_id = %s order by created_at desc", (user.id,)
    )


@router.post("", response_model=BriefingOut, status_code=status.HTTP_201_CREATED)
def create_briefing(body: BriefingIn, user: User = Depends(get_current_user)):
    return db.fetch_one(
        f"""
        insert into briefings (user_id, topic, time_of_day, timezone, next_run_at)
        values (%s, %s, %s, %s, %s)
        returning {COLUMNS}
        """,
        (user.id, body.topic.strip(), body.time_of_day, body.timezone,
         next_run_at(body.time_of_day, body.timezone)),
    )


@router.get("/{briefing_id}", response_model=BriefingOut)
def get_briefing(briefing_id: UUID, user: User = Depends(get_current_user)):
    return _get_owned(briefing_id, user)


@router.patch("/{briefing_id}", response_model=BriefingOut)
def update_briefing(briefing_id: UUID, body: BriefingPatch, user: User = Depends(get_current_user)):
    current = _get_owned(briefing_id, user)
    merged = {**current, **body.model_dump(exclude_none=True)}
    return db.fetch_one(
        f"""
        update briefings
        set topic = %s, time_of_day = %s, timezone = %s, is_active = %s, next_run_at = %s
        where id = %s and user_id = %s
        returning {COLUMNS}
        """,
        (merged["topic"].strip(), merged["time_of_day"], merged["timezone"], merged["is_active"],
         next_run_at(merged["time_of_day"], merged["timezone"]), briefing_id, user.id),
    )


@router.delete("/{briefing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_briefing(briefing_id: UUID, user: User = Depends(get_current_user)):
    if db.execute("delete from briefings where id = %s and user_id = %s", (briefing_id, user.id)) == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Briefing not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{briefing_id}/run", status_code=status.HTTP_202_ACCEPTED)
def run_now(briefing_id: UUID, user: User = Depends(get_current_user)):
    """Generate an episode immediately (doesn't change the daily schedule)."""
    _get_owned(briefing_id, user)
    try:
        episode = pipeline.start_episode(str(briefing_id), user.id)
    except pipeline.EpisodeInProgress:
        raise HTTPException(status.HTTP_409_CONFLICT, "An episode for this briefing is already being generated")
    return {"episode_id": episode["id"], "status": episode["status"]}
