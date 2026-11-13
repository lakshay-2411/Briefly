"""Daily scheduling: one in-memory cron job per active briefing.

The `briefings` table stays the source of truth:
- on startup every active briefing gets a job, missed runs are caught up,
  and episodes orphaned by a restart are marked failed;
- the API adds/replaces/removes a briefing's job whenever it changes;
- when a job fires, the run is claimed atomically via `next_run_at`, so a
  briefing can never run twice for the same day (double fire, catch-up, overlap).
"""

import logging
from datetime import datetime, time, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app import db, pipeline
from app.config import settings
from app.timeutil import next_run_at

log = logging.getLogger(__name__)

RECONCILE_JOB_ID = "reconcile"
RECONCILE_MINUTES = 30
STUCK_AFTER_MINUTES = 30

sched = BackgroundScheduler(
    timezone="UTC",
    job_defaults={"coalesce": True, "misfire_grace_time": 300, "max_instances": 1},
)


def _fire_time(time_of_day: time) -> time:
    """Local wall-clock time the job fires: the user's time minus the generation lead."""
    lead = timedelta(minutes=settings.generation_lead_minutes)
    return (datetime.combine(datetime.min, time_of_day) - lead).time()


def schedule_briefing(briefing: dict) -> None:
    """Create, replace or remove the job for a briefing row (id, time_of_day, timezone, is_active)."""
    job_id = str(briefing["id"])
    if not briefing["is_active"]:
        unschedule_briefing(job_id)
        return
    fire = _fire_time(briefing["time_of_day"])
    sched.add_job(
        run_due,
        CronTrigger(hour=fire.hour, minute=fire.minute, timezone=briefing["timezone"]),
        id=job_id,
        args=[job_id],
        replace_existing=True,
    )


def unschedule_briefing(briefing_id: str) -> None:
    if sched.get_job(str(briefing_id)):
        sched.remove_job(str(briefing_id))


def run_due(briefing_id: str) -> None:
    """Claim today's run for a briefing (if it's due) and start generating the episode."""
    row = db.fetch_one(
        """
        select user_id, time_of_day, timezone, next_run_at from briefings
        where id = %s and is_active and next_run_at <= now() + interval '1 minute'
        """,
        (briefing_id,),
    )
    if row is None:
        return  # not due (already claimed, paused, deleted, or rescheduled)

    # Next run strictly after the one being claimed, so an early fire can't reuse today's slot.
    after = max(datetime.now(timezone.utc), row["next_run_at"])
    claimed = db.execute(
        "update briefings set next_run_at = %s where id = %s and next_run_at = %s",
        (next_run_at(row["time_of_day"], row["timezone"], now=after), briefing_id, row["next_run_at"]),
    )
    if not claimed:
        return  # another fire / instance claimed it first

    try:
        episode = pipeline.start_episode(briefing_id, str(row["user_id"]))
        log.info("Scheduled run started: briefing %s -> episode %s", briefing_id, episode["id"])
    except pipeline.EpisodeInProgress:
        log.info("Briefing %s already has an episode in progress, skipping today's run", briefing_id)


def catch_up() -> None:
    """Run briefings whose time passed while the server was down."""
    for row in db.fetch_all("select id from briefings where is_active and next_run_at < now()"):
        log.info("Catching up missed run for briefing %s", row["id"])
        run_due(str(row["id"]))


def fail_stuck_episodes() -> None:
    """Episodes whose worker thread died (restart/crash) would otherwise stay 'in progress' forever."""
    n = db.execute(
        """
        update episodes set status = 'failed', error = 'Generation was interrupted (server restarted)'
        where status in ('researching', 'writing', 'synthesizing')
          and created_at < now() - make_interval(mins => %s)
        """,
        (STUCK_AFTER_MINUTES,),
    )
    if n:
        log.warning("Marked %d stuck episode(s) as failed", n)


def reconcile() -> None:
    """Make the in-memory jobs match the DB, then catch up anything missed. Safety net."""
    rows = db.fetch_all("select id, time_of_day, timezone, is_active from briefings where is_active")
    active = {str(r["id"]) for r in rows}
    for job in sched.get_jobs():
        if job.id != RECONCILE_JOB_ID and job.id not in active:
            job.remove()
    for r in rows:
        schedule_briefing(r)
    fail_stuck_episodes()
    catch_up()


def start() -> None:
    sched.start()
    sched.add_job(reconcile, "interval", minutes=RECONCILE_MINUTES, id=RECONCILE_JOB_ID, replace_existing=True)
    reconcile()
    log.info("Scheduler started with %d briefing job(s)", len(sched.get_jobs()) - 1)


def shutdown() -> None:
    sched.shutdown(wait=False)
