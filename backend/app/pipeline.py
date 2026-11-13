"""End-to-end episode generation: research -> script -> TTS -> storage -> email.

In the app, episodes run in a background thread pool via start_episode().
For local debugging it is also runnable from the CLI (writes to backend/output/):
    python -m app.pipeline "startup funding announced in the last 24 hours"
    python -m app.pipeline --tts-only "Hello, this is a short test."
"""

import argparse
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from psycopg.types.json import Jsonb

from app import db
from app.config import settings
from app.services import email, research, storage, tts

log = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="episode")


class EpisodeInProgress(Exception):
    pass


def start_episode(briefing_id: str, user_id: str) -> dict:
    """Create an episode row and generate it in the background. Returns the new episode."""
    episode = db.fetch_one(
        """
        insert into episodes (briefing_id, user_id, status)
        select %s, %s, 'researching'
        where not exists (
            select 1 from episodes
            where briefing_id = %s and status in ('researching', 'writing', 'synthesizing')
        )
        returning id, briefing_id, status, created_at
        """,
        (briefing_id, user_id, briefing_id),
    )
    if episode is None:
        raise EpisodeInProgress(briefing_id)
    executor.submit(run_episode, str(episode["id"]))
    return episode


def _set(episode_id: str, **fields) -> None:
    cols = ", ".join(f"{k} = %({k})s" for k in fields)
    db.execute(f"update episodes set {cols} where id = %(id)s", {**fields, "id": episode_id})


def run_episode(episode_id: str) -> None:
    row = db.fetch_one(
        """
        select e.user_id, b.topic, u.email
        from episodes e
        join briefings b on b.id = e.briefing_id
        join auth.users u on u.id = e.user_id
        where e.id = %s
        """,
        (episode_id,),
    )
    if row is None:
        log.warning("Episode %s vanished before it could run", episode_id)
        return

    try:
        log.info("[%s] researching %r", episode_id, row["topic"])
        articles = research.gather_articles(research.plan_queries(row["topic"]))
        if not articles:
            raise RuntimeError("No recent articles found for this topic")

        _set(episode_id, status="writing")
        result = research.write_script(row["topic"], articles)

        _set(
            episode_id,
            status="synthesizing",
            title=result["title"],
            summary=result["summary"],
            script=result["script"],
            sources=Jsonb(result["sources"]),
        )
        mp3, duration = tts.synthesize(result["script"])

        audio_path = f"{row['user_id']}/{episode_id}.mp3"
        storage.upload_mp3(audio_path, mp3)
        _set(episode_id, status="ready", audio_path=audio_path, duration_seconds=duration)
        log.info("[%s] ready (%ds)", episode_id, duration)
    except Exception as e:
        log.exception("[%s] failed", episode_id)
        _set(episode_id, status="failed", error=str(e)[:1000])
        return

    try:
        email.send_episode_email(
            row["email"], result["title"], result["summary"], f"{settings.frontend_url}/episodes/{episode_id}"
        )
    except Exception:
        # The episode itself is fine; don't mark it failed because of email.
        log.exception("[%s] email failed", episode_id)


# ---------- CLI (local debugging, no DB) ----------

def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "episode"


def run_local(topic: str) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    slug = _slug(topic)
    episode = research.research(topic)
    log.info("Script ready: %r (%d words)", episode["title"], len(episode["script"].split()))
    (OUTPUT_DIR / f"{slug}.json").write_text(json.dumps(episode, indent=2, ensure_ascii=False))
    mp3, duration = tts.synthesize(episode["script"])
    mp3_path = OUTPUT_DIR / f"{slug}.mp3"
    mp3_path.write_bytes(mp3)
    log.info("Audio saved: %s (%ds, %.1f MB)", mp3_path, duration, len(mp3) / 1e6)
    return mp3_path


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    parser = argparse.ArgumentParser(description="Generate one podcast episode locally")
    parser.add_argument("topic", help="research topic, or text to speak with --tts-only")
    parser.add_argument("--tts-only", action="store_true", help="only synthesize the given text")
    args = parser.parse_args()

    if args.tts_only:
        OUTPUT_DIR.mkdir(exist_ok=True)
        mp3, duration = tts.synthesize(args.topic)
        path = OUTPUT_DIR / "tts-test.mp3"
        path.write_bytes(mp3)
        log.info("Saved %s (%ds)", path, duration)
        return

    run_local(args.topic)


if __name__ == "__main__":
    main()
