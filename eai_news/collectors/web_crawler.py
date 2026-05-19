from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from ..models import RawItem
from .base import BaseCollector

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


class WebCrawler(BaseCollector):
    """Crawl news/blog pages to discover article links."""

    def __init__(
        self,
        source_id: str,
        source_name: str,
        index_url: str,
        article_selector: str = "a[href]",
        max_age_days: int = 7,
    ):
        self.source_id = source_id
        self.source_name = source_name
        self.index_url = index_url
        self.article_selector = article_selector
        self.max_age_days = max_age_days
        self._base = f"{urlparse(index_url).scheme}://{urlparse(index_url).netloc}"

    async def fetch(self) -> list[RawItem]:
        async with httpx.AsyncClient(timeout=20, headers=HEADERS, follow_redirects=True) as client:
            resp = await client.get(self.index_url)
            resp.raise_for_status()
            html = resp.text

        soup = BeautifulSoup(html, "lxml")
        links = soup.select(self.article_selector)
        seen_urls: set[str] = set()
        items = []

        for tag in links[:40]:
            href = tag.get("href", "")
            if not href or href.startswith("#") or href.startswith("javascript"):
                continue

            full_url = urljoin(self._base, href)
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            # Only keep links within the same domain
            if urlparse(full_url).netloc != urlparse(self._base).netloc:
                continue

            title = tag.get_text(strip=True) or tag.get("title", "")
            if len(title) < 5:
                # Try parent element for title
                parent = tag.parent
                if parent:
                    title = parent.get_text(strip=True)[:120]

            if not title:
                continue

            items.append(RawItem(
                source_id=self.source_id,
                source_name=self.source_name,
                url=full_url,
                title=title[:200],
                content="",
                published_at=None,   # web crawlers rarely expose publish time on index
                raw_metadata={"index_url": self.index_url},
            ))

        return items
