import asyncio
from urllib.parse import urljoin, urlparse

import httpx
import trafilatura
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

_CONTENT_FETCH_LIMIT = 5      # 每个源最多拉多少条文章正文
_SEMAPHORE = asyncio.Semaphore(3)  # 全局并发上限


def _extract_first_para(html: str, max_chars: int = 200) -> str:
    text = trafilatura.extract(html, include_comments=False, include_tables=False) or ""
    for line in text.split("\n"):
        line = line.strip()
        if len(line) > 20:   # 过滤掉导航残留的短行
            return line[:max_chars]
    return ""


class WebCrawler(BaseCollector):
    """Crawl news/blog index pages to discover article links, then fetch
    content for the first few articles."""

    def __init__(
        self,
        source_id: str,
        source_name: str,
        index_url: str,
        article_selector: str = "a[href]",
        allow_external: bool = False,
    ):
        self.source_id = source_id
        self.source_name = source_name
        self.index_url = index_url
        self.article_selector = article_selector
        self.allow_external = allow_external
        self._base = f"{urlparse(index_url).scheme}://{urlparse(index_url).netloc}"

    async def fetch(self) -> list[RawItem]:
        async with httpx.AsyncClient(timeout=20, headers=HEADERS, follow_redirects=True) as client:
            resp = await client.get(self.index_url)
            resp.raise_for_status()
            html = resp.text

        soup = BeautifulSoup(html, "lxml")
        links = soup.select(self.article_selector)
        seen_urls: set[str] = set()
        items: list[RawItem] = []

        for tag in links[:40]:
            href = tag.get("href", "")
            if not href or href.startswith("#") or href.startswith("javascript"):
                continue

            full_url = urljoin(self._base, href)
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            if not self.allow_external and urlparse(full_url).netloc != urlparse(self._base).netloc:
                continue

            title = tag.get_text(strip=True) or tag.get("title", "")
            if len(title) < 5:
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
                published_at=None,
                raw_metadata={"index_url": self.index_url},
            ))

        # Fetch article content for the first N items
        if items:
            await self._fill_content(items[:_CONTENT_FETCH_LIMIT])

        return items

    async def _fill_content(self, items: list[RawItem]) -> None:
        async with httpx.AsyncClient(timeout=15, headers=HEADERS, follow_redirects=True) as client:
            tasks = [self._fetch_one_content(client, item) for item in items]
            await asyncio.gather(*tasks)

    async def _fetch_one_content(self, client: httpx.AsyncClient, item: RawItem) -> None:
        async with _SEMAPHORE:
            try:
                resp = await client.get(item.url)
                resp.raise_for_status()
                item.content = _extract_first_para(resp.text)
            except Exception as e:
                logger.debug(f"[{self.source_name}] content fetch failed for {item.url}: {e}")
