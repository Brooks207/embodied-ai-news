import asyncio
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser

from ..models import RawItem
from .base import BaseCollector


class RSSCollector(BaseCollector):
    def __init__(self, source_id: str, source_name: str, feed_url: str):
        self.source_id = source_id
        self.source_name = source_name
        self.feed_url = feed_url

    async def fetch(self) -> list[RawItem]:
        loop = asyncio.get_event_loop()
        feed = await loop.run_in_executor(None, feedparser.parse, self.feed_url)

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
