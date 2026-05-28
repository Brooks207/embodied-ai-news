"""
PlaywrightCrawler — 无头浏览器采集器，用于 JS 渲染（CSR）页面。

与 WebCrawler 接口完全一致，额外支持：
  - wait_selector：等待指定元素出现后再解析 HTML（默认 networkidle）
  - use_browser: true  在 sources.yaml 中标记，由 __init__.py 自动路由到这里

浏览器实例进程内懒加载，所有 PlaywrightCrawler 共享同一个 Chromium 进程。
"""
import asyncio
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from ..models import RawItem
from .base import BaseCollector
from .web_crawler import HEADERS, _extract_first_para, _extract_title

# ── 全局 Chromium 实例（懒加载，进程内共享）────────────────────────────
_browser = None
_pw = None
_browser_lock = asyncio.Lock()


async def _get_browser():
    global _browser, _pw
    async with _browser_lock:
        if _browser is None or not _browser.is_connected():
            from playwright.async_api import async_playwright
            logger.info("Playwright: launching Chromium...")
            _pw = await async_playwright().start()
            _browser = await _pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
            logger.info("Playwright: Chromium ready")
    return _browser


async def close_browser():
    """进程退出或不再需要时调用，释放 Chromium 资源。"""
    global _browser, _pw
    if _browser:
        try:
            await _browser.close()
        except Exception:
            pass
        _browser = None
    if _pw:
        try:
            await _pw.stop()
        except Exception:
            pass
        _pw = None


# 同时最多 2 个活跃页面，避免内存爆炸
_PAGE_SEM = asyncio.Semaphore(2)

_CONTENT_FETCH_LIMIT = 5


class PlaywrightCrawler(BaseCollector):
    """无头浏览器采集器，适用于 React/Vue CSR 页面。"""

    def __init__(
        self,
        source_id: str,
        source_name: str,
        index_url: str,
        article_selector: str = "a[href]",
        allow_external: bool = False,
        wait_selector: str | None = None,
    ):
        self.source_id = source_id
        self.source_name = source_name
        self.index_url = index_url
        self.article_selector = article_selector
        self.allow_external = allow_external
        self.wait_selector = wait_selector  # 出现后才开始解析
        self._base = f"{urlparse(index_url).scheme}://{urlparse(index_url).netloc}"

    async def fetch(self) -> list[RawItem]:
        browser = await _get_browser()

        async with _PAGE_SEM:
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                locale="zh-CN",
                extra_http_headers={"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
            )
            try:
                page = await context.new_page()
                await page.goto(
                    self.index_url,
                    wait_until="networkidle",
                    timeout=30_000,
                )
                if self.wait_selector:
                    try:
                        await page.wait_for_selector(
                            self.wait_selector, timeout=10_000
                        )
                    except Exception:
                        logger.debug(
                            f"[{self.source_name}] wait_selector '{self.wait_selector}' timed out, proceeding anyway"
                        )
                html = await page.content()
            except Exception as e:
                logger.warning(f"[{self.source_name}] Playwright page load failed: {e}")
                return []
            finally:
                await context.close()

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

            seen_urls.add(full_url)
            items.append(
                RawItem(
                    source_id=self.source_id,
                    source_name=self.source_name,
                    url=full_url,
                    title=title[:200],
                    content="",
                    published_at=None,
                    raw_metadata={"index_url": self.index_url},
                )
            )

        logger.info(f"[{self.source_name}] Playwright found {len(items)} items")

        if items:
            await self._fill_content(items[:_CONTENT_FETCH_LIMIT])

        return items

    async def _fill_content(self, items: list[RawItem]) -> None:
        async with httpx.AsyncClient(
            timeout=15, headers=HEADERS, follow_redirects=True
        ) as client:
            tasks = [self._fetch_one_content(client, item) for item in items]
            await asyncio.gather(*tasks)

    async def _fetch_one_content(
        self, client: httpx.AsyncClient, item: RawItem
    ) -> None:
        try:
            resp = await client.get(item.url)
            resp.raise_for_status()
            item.content = _extract_first_para(resp.text)
        except Exception as e:
            logger.debug(
                f"[{self.source_name}] content fetch failed for {item.url}: {e}"
            )
