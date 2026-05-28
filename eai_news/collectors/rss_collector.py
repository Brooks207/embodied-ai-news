from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import httpx
from loguru import logger

from ..models import RawItem
from .base import BaseCollector

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; EAI-News-Bot/1.0)",
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml",
}


async def _fetch_feed_bytes(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=20, headers=_HEADERS, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content


class RSSCollector(BaseCollector):
    def __init__(self, source_id: str, source_name: str, feed_url: str):
        self.source_id = source_id
        self.source_name = source_name
        self.feed_url = feed_url

    async def fetch(self) -> list[RawItem]:
        raw_bytes = await _fetch_feed_bytes(self.feed_url)
        feed = feedparser.parse(raw_bytes)

        if feed.bozo and not feed.entries:
            logger.warning(
                f"[{self.source_name}] feedparser parse error: {feed.bozo_exception}"
            )
        elif not feed.entries:
            logger.warning(f"[{self.source_name}] feed parsed OK but 0 entries")

        items = []
        for entry in feed.entries[:30]:
            url = entry.get("link", "")
            if not url:
                continue

            published_at = None
            if hasattr(entry, "published"):
                try:
                    published_at = parsedate_to_datetime(entry.published)
                    if published_at.tzinfo is None:
                        published_at = published_at.replace(tzinfo=timezone.utc)
                except Exception:
                    pass
            if published_at is None and hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                except Exception:
                    pass

            items.append(RawItem(
                source_id=self.source_id,
                source_name=self.source_name,
                url=url,
                title=entry.get("title", "").strip(),
                content=entry.get("summary", ""),
                published_at=published_at,
                raw_metadata={"feed_url": self.feed_url},
            ))
        return items
