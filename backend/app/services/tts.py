"""Gnani.ai TTS: script -> sentence chunks -> raw PCM per chunk -> one MP3."""

import logging
import re
import threading
import time

import httpx
import lameenc

from app.config import settings

log = logging.getLogger(__name__)

GNANI_URL = "https://api.vachana.ai/api/v1/tts/inference"
SAMPLE_RATE = 24000
SAMPLE_WIDTH = 2  # 16-bit
MP3_KBPS = 64

# Gnani allows only one active request per account, so all synthesis is serialized.
_lock = threading.Lock()


class TTSError(Exception):
    pass


def chunk_text(text: str, max_chars: int) -> list[str]:
    """Split text into chunks <= max_chars, breaking on sentence ends (then commas, then spaces)."""
    sentences = re.split(r"(?<=[.!?])\s+", " ".join(text.split()))
    pieces: list[str] = []
    for s in sentences:
        while len(s) > max_chars:
            cut = s.rfind(", ", 0, max_chars)
            cut = cut + 1 if cut > 0 else s.rfind(" ", 0, max_chars)
            if cut <= 0:
                cut = max_chars
            pieces.append(s[:cut].strip())
            s = s[cut:].strip()
        if s:
            pieces.append(s)

    chunks, current = [], ""
    for p in pieces:
        if current and len(current) + 1 + len(p) > max_chars:
            chunks.append(current)
            current = p
        else:
            current = f"{current} {p}".strip()
    if current:
        chunks.append(current)
    return chunks


def _synthesize_chunk(client: httpx.Client, text: str) -> bytes:
    body = {
        "text": text,
        "model": settings.gnani_model,
        "voice": settings.gnani_voice_id or "Kaveri",
        "language": settings.gnani_language,
        "speed": 1.0,
        "audio_config": {
            "sample_rate": SAMPLE_RATE,
            "num_channels": 1,
            "sample_width": SAMPLE_WIDTH,
            "encoding": "linear_pcm",
            "container": "raw",
        },
    }
    for attempt in range(4):
        resp = client.post(GNANI_URL, json=body)
        if resp.status_code == 200:
            return resp.content
        # 429 = another request still active; 5xx = transient. Back off and retry.
        if resp.status_code in (429, 500, 502, 503) and attempt < 3:
            log.warning("Gnani returned %s, retrying: %s", resp.status_code, resp.text[:200])
            time.sleep(2 * (attempt + 1))
            continue
        raise TTSError(f"Gnani TTS failed ({resp.status_code}): {resp.text[:300]}")
    raise TTSError("Gnani TTS failed after retries")


def synthesize(script: str) -> tuple[bytes, int]:
    """Return (mp3_bytes, duration_seconds)."""
    chunks = chunk_text(script, settings.gnani_max_chars)
    log.info("Synthesizing %d chunks", len(chunks))
    pcm = bytearray()
    with _lock, httpx.Client(
        headers={"X-API-Key-ID": settings.gnani_api_key},
        timeout=httpx.Timeout(120.0, connect=10.0),
    ) as client:
        for i, chunk in enumerate(chunks, 1):
            log.info("TTS chunk %d/%d (%d chars)", i, len(chunks), len(chunk))
            pcm += _synthesize_chunk(client, chunk)

    encoder = lameenc.Encoder()
    encoder.set_bit_rate(MP3_KBPS)
    encoder.set_in_sample_rate(SAMPLE_RATE)
    encoder.set_channels(1)
    encoder.set_quality(2)
    mp3 = encoder.encode(bytes(pcm)) + encoder.flush()
    duration = round(len(pcm) / (SAMPLE_RATE * SAMPLE_WIDTH))
    return bytes(mp3), duration
