"""JSON-output LLM calls: Groq's free models first, then OpenRouter's free models.

Groq's free tier limits tokens per minute *per model*, so moving to the next Groq model
on a 429 is usually enough. If every model is rate-limited, wait for the minute to reset
and go through the list once more.
"""

import json
import logging
import time

import httpx

from app.config import settings

log = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
TIMEOUT = httpx.Timeout(90.0, connect=10.0)
RATE_LIMIT_WAIT_SECONDS = 60


class LLMError(Exception):
    pass


def _models(csv: str) -> list[str]:
    return [m.strip() for m in csv.split(",") if m.strip()]


def _chat(url: str, api_key: str, model: str, system: str, prompt: str) -> str:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.6,
    }
    if "gpt-oss" in model:
        body["reasoning_effort"] = "low"  # reasoning tokens count against the per-minute limit
    resp = httpx.post(url, headers={"Authorization": f"Bearer {api_key}"}, json=body, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"] or ""


def _parse_json(text: str) -> dict:
    # Some models wrap JSON in markdown fences or add a sentence around it.
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in model output")
    return json.loads(text[start : end + 1])


def generate_json(system: str, prompt: str) -> dict:
    """Return the model's JSON answer as a dict, trying each model in order until one works."""
    attempts = [(GROQ_URL, settings.groq_api_key, m) for m in _models(settings.groq_models)]
    if settings.openrouter_api_key:
        attempts += [(OPENROUTER_URL, settings.openrouter_api_key, m) for m in _models(settings.openrouter_models)]

    last_error: Exception | None = None
    for round_ in range(2):
        rate_limited = False
        for url, key, model in attempts:
            try:
                result = _parse_json(_chat(url, key, model, system, prompt))
                log.info("LLM answered via %s", model)
                return result
            except httpx.HTTPStatusError as e:
                rate_limited |= e.response.status_code == 429
                last_error = e
                log.warning("LLM %s failed: %s %s", model, e.response.status_code, e.response.text[:200])
            except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
                last_error = e
                log.warning("LLM %s failed: %s", model, e)
        if round_ == 0 and rate_limited:
            log.info("All models failed and some were rate-limited; retrying in %ds", RATE_LIMIT_WAIT_SECONDS)
            time.sleep(RATE_LIMIT_WAIT_SECONDS)
        else:
            break
    raise LLMError(f"All LLM providers failed: {last_error}")
