"""Web search via Tavily (free tier: 1 credit per basic search)."""

import httpx

from app.config import settings

TAVILY_URL = "https://api.tavily.com/search"


def search_news(query: str, time_range: str = "day", max_results: int = 5) -> list[dict]:
    resp = httpx.post(
        TAVILY_URL,
        headers={"Authorization": f"Bearer {settings.tavily_api_key}"},
        json={
            "query": query,
            "topic": "news",
            "time_range": time_range,
            "search_depth": "basic",
            "max_results": max_results,
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    return [
        {
            "title": r.get("title", ""),
            "url": r["url"],
            "content": r.get("content", ""),
            "published_date": r.get("published_date"),
        }
        for r in resp.json().get("results", [])
        if r.get("url")
    ]
