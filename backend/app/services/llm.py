"""JSON-output LLM calls: Gemini (free tier) first, a second Gemini model, then Groq."""

import json
import logging
import time

import httpx

from app.config import settings

log = logging.getLogger(__name__)

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
TIMEOUT = httpx.Timeout(90.0, connect=10.0)


class LLMError(Exception):
    pass


def _gemini(system: str, prompt: str, model: str) -> str:
    resp = httpx.post(
        GEMINI_URL.format(model=model),
        headers={"x-goog-api-key": settings.gemini_api_key},
        json={
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.6},
        },
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    parts = resp.json()["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts)


def _groq(system: str, prompt: str) -> str:
    resp = httpx.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {settings.groq_api_key}"},
        json={
            "model": settings.groq_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.6,
        },
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def generate_json(system: str, prompt: str) -> dict:
    """Return the model's JSON answer as a dict. Tries each provider in order until one works."""
    attempts = [
        (settings.gemini_model, lambda: _gemini(system, prompt, settings.gemini_model)),
        (settings.gemini_fallback_model, lambda: _gemini(system, prompt, settings.gemini_fallback_model)),
        (settings.groq_model, lambda: _groq(system, prompt)),
    ]
    last_error: Exception | None = None
    for name, call in attempts:
        try:
            return json.loads(call())
        except (httpx.HTTPError, KeyError, IndexError, json.JSONDecodeError) as e:
            last_error = e
            log.warning("LLM call via %s failed: %s", name, e)
            time.sleep(2)
    raise LLMError(f"All LLM providers failed: {last_error}")
