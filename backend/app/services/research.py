"""Research agent: plan search queries -> search the web -> write a ~5 minute script."""

import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from app.services import llm, search

log = logging.getLogger(__name__)

TARGET_WORDS = 850  # ~5 minutes at the Gnani voice's ~172 words per minute
MIN_WORDS, MAX_WORDS = 600, 1100
MIN_ARTICLES = 4
MAX_ARTICLES = 10


def _today(tz: str) -> str:
    """Today's date as the listener sees it."""
    return datetime.now(ZoneInfo(tz)).strftime("%A, %d %B %Y")


def plan_queries(topic: str, tz: str = "UTC") -> list[str]:
    system = (
        "You are a research planner for a daily news podcast. "
        "Given a topic, produce focused web search queries that will surface the latest news on it. "
        'Reply with JSON: {"queries": ["...", "..."]}'
    )
    prompt = f"Today is {_today(tz)}.\nTopic: {topic}\n\nWrite 3 to 5 distinct, specific search queries."
    queries = llm.generate_json(system, prompt).get("queries") or []
    return [q for q in queries if isinstance(q, str) and q.strip()][:5] or [topic]


def gather_articles(queries: list[str]) -> list[dict]:
    def run(time_range: str) -> list[dict]:
        seen, articles = set(), []
        for q in queries:
            try:
                results = search.search_news(q, time_range=time_range)
            except Exception as e:  # one failing query shouldn't kill the episode
                log.warning("Search failed for %r: %s", q, e)
                continue
            for r in results:
                if r["url"] not in seen:
                    seen.add(r["url"])
                    articles.append(r)
        return articles

    articles = run("day")
    if len(articles) < MIN_ARTICLES:
        log.info("Only %d articles from the last day, widening to last week", len(articles))
        articles = run("week")
    return articles[:MAX_ARTICLES]


SCRIPT_SYSTEM = f"""You write scripts for a daily audio news briefing that is read aloud by a text-to-speech voice.

Rules:
- Use ONLY facts found in the provided articles. Never invent names, numbers or events.
- Prefer the most recent and most important items; group related items together.
- Write for the ear: plain spoken English, short sentences, natural transitions.
- No markdown, no bullet points, no headings, no emojis, no URLs, no stage directions.
- Write numbers, currencies and dates as they should be spoken (e.g. "twenty five million dollars").
- Structure: a one or two sentence intro naming the topic and date, then the stories, then a short sign-off.
- If the articles contain little genuinely new information, say so briefly instead of padding.
- Length: about {TARGET_WORDS} words (roughly five minutes spoken).

Reply with JSON:
{{"title": "short episode title", "summary": "2-3 sentence summary for an email", "script": "the full spoken script", "sources": [{{"title": "...", "url": "..."}}]}}
"sources" must list only the articles you actually used, with URLs copied exactly."""


def _articles_block(articles: list[dict]) -> str:
    blocks = []
    for i, a in enumerate(articles, 1):
        blocks.append(
            f"[{i}] {a['title']}\nURL: {a['url']}\nPublished: {a.get('published_date') or 'unknown'}\n"
            f"{a['content'][:800]}"
        )
    return "\n\n".join(blocks)


def write_script(topic: str, articles: list[dict], tz: str = "UTC") -> dict:
    prompt = (
        f"Today is {_today(tz)}.\nPodcast topic: {topic}\n\n"
        f"Articles ({len(articles)}):\n\n{_articles_block(articles)}"
    )
    result = llm.generate_json(SCRIPT_SYSTEM, prompt)

    words = len(result.get("script", "").split())
    if not MIN_WORDS <= words <= MAX_WORDS:
        log.info("Script has %d words, asking for a revision to ~%d", words, TARGET_WORDS)
        revise = (
            f"{prompt}\n\nHere is a draft that is {words} words long, but it must be about "
            f"{TARGET_WORDS} words. Rewrite it to that length following all the rules "
            f"(only expand using facts from the articles).\n\nDraft JSON:\n{json.dumps(result)}"
        )
        revised = llm.generate_json(SCRIPT_SYSTEM, revise)
        if revised.get("script"):
            result = revised

    if not result.get("script"):
        raise llm.LLMError("LLM returned no script")

    # Keep only sources that really came from the search results.
    known = {a["url"]: a["title"] for a in articles}
    sources = [
        {"title": s.get("title") or known[s["url"]], "url": s["url"]}
        for s in result.get("sources", [])
        if isinstance(s, dict) and s.get("url") in known
    ]
    return {
        "title": result.get("title") or topic,
        "summary": result.get("summary", ""),
        "script": result["script"].strip(),
        "sources": sources or [{"title": t, "url": u} for u, t in known.items()],
    }


def research(topic: str) -> dict:
    queries = plan_queries(topic)
    log.info("Search queries: %s", queries)
    articles = gather_articles(queries)
    log.info("Collected %d articles", len(articles))
    if not articles:
        raise RuntimeError("No articles found for this topic")
    return write_script(topic, articles)
