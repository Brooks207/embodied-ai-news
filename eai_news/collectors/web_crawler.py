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

# 无意义的通用锚文字，遇到时向上找标题元素
_GENERIC_TITLES = frozenset({
    "read more", "read blog", "read post", "learn more", "view more",
    "see more", "more", "news", "stories", "blog", "click here",
    "details", "more details", "explore", "discover", "view", "open",
    "go", "link",
})


def _extract_title(tag) -> str:
    """从 <a> 标签提取有意义的标题。

    优先级：
    ① <a> 内的 heading 子元素（h1-h6）
    ② <a> 自身文字（非通用短语、长度 ≥ 5）
    ③ 父容器内的 heading（仅当 ① / ② 失败时）
    → 若以上全部失败，返回 "" ，让调用方保持该 URL 未认领，
      等待同一 URL 的后续 <a>（如纯文字标题链接）来提供正确标题。
    """
    # ① <a> 内有 heading 子元素（如 <h3>/<h4> 等）直接用
    heading = tag.find(["h1", "h2", "h3", "h4", "h5", "h6"])
    if heading:
        return heading.get_text(strip=True)[:200]

    # ① ½ card 布局：≥2 个 <p> 标签时，最后一个通常是标题（前面是分类/日期）
    paras = tag.find_all("p")
    if len(paras) >= 2:
        last_para = paras[-1].get_text(strip=True)
        if len(last_para) >= 10:
            return last_para[:200]

    # ② 用 <a> 自身文字
    title = tag.get_text(strip=True) or tag.get("title", "")

    # ③ 文字太短或是通用短语 → 去父容器找 heading（只接受 heading，不回退到全文）
    if len(title) < 5 or title.lower() in _GENERIC_TITLES:
        parent = tag.parent
        if parent:
            heading = parent.find(["h1", "h2", "h3", "h4", "h5", "h6"])
            if heading:
                return heading.get_text(strip=True)[:200]
        return ""  # 无法提取有效标题，返回空让 URL 保持未认领

    return title


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

            if not self.allow_external and urlparse(full_url).netloc != urlparse(self._base).netloc:
                continue

            title = _extract_title(tag)

            if not title:
                continue

            seen_urls.add(full_url)  # only mark seen after confirming item will be created

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
