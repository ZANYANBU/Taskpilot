import json
import logging
import re
from typing import List

import feedparser
import requests

from ..constants import REGION_CODES, UA_HEADERS


LOGGER = logging.getLogger("taskpilot.topics")


def _fetch_json(url: str) -> dict:
    try:
        response = requests.get(url, headers=UA_HEADERS, timeout=10)
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        status = getattr(exc.response, "status_code", "N/A")
        LOGGER.warning("Google Trends request failed (%s): %s", status, exc)
        return {}
    except requests.exceptions.RequestException as exc:
        LOGGER.warning("Google Trends request error: %s", exc)
        return {}

    clean = re.sub(r"^.*?\n", "", response.text, count=1).strip()
    return json.loads(clean) if clean.startswith("{") else {}


def google_trends(region: str, keyword: str | None = None, limit: int = 5) -> List[str]:
    geo = REGION_CODES.get(region, "US")
    data = _fetch_json(f"https://trends.google.com/trends/api/dailytrends?geo={geo}")
    if not data:
        return []

    days = data.get("default", {}).get("trendingSearchesDays", [])
    trends = [
        item["title"]["query"]
        for day in days
        for item in day.get("trendingSearches", [])
    ]
    if keyword:
        trends = [t for t in trends if keyword.lower() in t.lower()]
    return trends[:limit]


def bing_news(keyword: str | None = None, limit: int = 5) -> List[str]:
    query = requests.utils.quote(keyword or "news")
    rss_url = f"https://www.bing.com/news/search?q={query}&format=RSS"
    feed = feedparser.parse(rss_url)
    return [entry.title for entry in feed.entries][:limit]


def get_topics(keyword: str | None, region: str) -> List[str]:
    topics = google_trends(region, keyword)
    return topics if topics else bing_news(keyword)
