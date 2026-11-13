"""End-to-end episode generation.

Phase 1: runnable from the CLI, writes output to backend/output/.
    python -m app.pipeline "startup funding announced in the last 24 hours" --email you@example.com
    python -m app.pipeline --tts-only "Hello, this is a short test."
"""

import argparse
import json
import logging
import re
from pathlib import Path

from app.config import settings
from app.services import email, research, tts

log = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "episode"


def run_local(topic: str, to_email: str | None) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    slug = _slug(topic)

    log.info("Researching: %s", topic)
    episode = research.research(topic)
    log.info("Script ready: %r (%d words)", episode["title"], len(episode["script"].split()))
    (OUTPUT_DIR / f"{slug}.json").write_text(json.dumps(episode, indent=2, ensure_ascii=False))

    log.info("Synthesizing audio")
    mp3, duration = tts.synthesize(episode["script"])
    mp3_path = OUTPUT_DIR / f"{slug}.mp3"
    mp3_path.write_bytes(mp3)
    log.info("Audio saved: %s (%ds, %.1f MB)", mp3_path, duration, len(mp3) / 1e6)

    if to_email:
        # Real episode pages arrive in Phase 2; this link is a placeholder.
        email.send_episode_email(
            to_email, episode["title"], episode["summary"], f"{settings.frontend_url}/episodes/local-test"
        )
        log.info("Email sent to %s", to_email)
    return mp3_path


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    parser = argparse.ArgumentParser(description="Generate one podcast episode locally")
    parser.add_argument("topic", help="research topic, or text to speak with --tts-only")
    parser.add_argument("--email", help="send the episode email to this address")
    parser.add_argument("--tts-only", action="store_true", help="only synthesize the given text")
    args = parser.parse_args()

    if args.tts_only:
        OUTPUT_DIR.mkdir(exist_ok=True)
        mp3, duration = tts.synthesize(args.topic)
        path = OUTPUT_DIR / "tts-test.mp3"
        path.write_bytes(mp3)
        log.info("Saved %s (%ds)", path, duration)
        return

    run_local(args.topic, args.email)


if __name__ == "__main__":
    main()
