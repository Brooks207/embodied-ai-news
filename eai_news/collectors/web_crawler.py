import asyncio
import json
import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
import trafilatura
from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser
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


_DATE_META_PROPS = {
    "article:published_time", "article:modified_time", "og:updated_time",
    "date", "pubdate", "publishdate", "dcterms.date", "dc.date", "datepublished",
}

_URL_DATE_RE = re.compile(r"/(\d{4})[/-](\d{2})[/-](\d{2})[/\-_]")

# CSS classes that typically wrap visible date text
_DATE_CLASS_RE = re.compile(r'\bdate\b|\btime\b|\bpublish|\bposted|\bcreated|\brelease', re.I)

# ISO dates embedded in Next.js __NEXT_DATA__ / RSC payloads
_EMBEDDED_ISO_RE = re.compile(r'"(?:date|datePublished|createdAt|publishedAt|pubDate)"\s*:\s*"(20\d{2}-\d{2}-\d{2}(?:T[^"]{0,30})?)"')

# YYYYMMDD compact format (must be plausible: 2020-2039, month 01-12, day 01-31)
_YYYYMMDD_RE = re.compile(r'\b(20[2-3]\d)([01]\d)([0-3]\d)\b')

# English month-name date: "April 28, 2026", "February 19, 2026", "May 13, 2026"
_MONTH_DATE_RE = re.compile(
    r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
    r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
    r'\s+\d{1,2}(?:st|nd|rd|th)?,?\s+20[2-9]\d\b', re.I
)


def _parse_date_str(s: str) -> Optional[datetime]:
    s = s.strip()
    if not s or len(s) < 4:
        return None
    try:
        dt = dateutil_parser.parse(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _parse_yyyymmdd(s: str) -> Optional[datetime]:
    m = _YYYYMMDD_RE.search(s)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def _extract_published_date(html: str, url: str = "") -> Optional[datetime]:
    """Extract publish date from article HTML.

    Priority: JSON-LD → <meta> → <time> → __NEXT_DATA__/RSC → CSS class text → YYYYMMDD → URL
    """
    soup = BeautifulSoup(html, "lxml")

    # 1. JSON-LD (standard and @graph)
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                # flat keys
                for key in ("datePublished", "dateCreated", "dateModified"):
                    if item.get(key):
                        dt = _parse_date_str(item[key])
                        if dt:
                            return dt
                # @graph array
                for g in item.get("@graph", []):
                    if isinstance(g, dict):
                        for key in ("datePublished", "dateCreated", "dateModified"):
                            if g.get(key):
                                dt = _parse_date_str(g[key])
                                if dt:
                                    return dt
        except Exception:
            pass

    # 2. <meta> tags
    for tag in soup.find_all("meta"):
        name = (tag.get("property") or tag.get("name") or "").lower()
        if name in _DATE_META_PROPS:
            dt = _parse_date_str(tag.get("content", ""))
            if dt:
                return dt

    # 3. <time> element with datetime attribute
    for time_tag in soup.find_all("time"):
        dt_attr = time_tag.get("datetime", "")
        if dt_attr:
            dt = _parse_date_str(dt_attr)
            if dt:
                return dt

    # 4. __NEXT_DATA__ and Next.js RSC / inline JSON payloads
    m = _EMBEDDED_ISO_RE.search(html)
    if m:
        dt = _parse_date_str(m.group(1))
        if dt:
            return dt

    # 5. CSS class-based visible date text (e.g. <p class="date">, <div class="time">)
    for el in soup.find_all(class_=_DATE_CLASS_RE):
        txt = el.get_text(strip=True)
        dt = _parse_date_str(txt) or _parse_yyyymmdd(txt)
        if dt:
            return dt

    # 5b. English month-name dates anywhere in HTML (JS-rendered press releases):
    #     "April 28, 2026", "February 19, 2026", "May 13, 2026"
    m_month = _MONTH_DATE_RE.search(html)
    if m_month:
        dt = _parse_date_str(m_month.group(0))
        if dt:
            return dt

    # 6. YYYYMMDD compact format anywhere in page
    dt = _parse_yyyymmdd(html)
    if dt:
        return dt

    # 7. Plain text date in elements that contain "发布时间" or "date" label keywords
    _PUB_LABEL_RE = re.compile(r'发布时间[：:]\s*(20\d{2}[-/年]\d{1,2}[-/月]\d{1,2})', re.IGNORECASE)
    m3 = _PUB_LABEL_RE.search(html)
    if m3:
        dt = _parse_date_str(m3.group(1))
        if dt:
            return dt

    # 8. URL date pattern /2024/05/21/
    if url:
        m2 = _URL_DATE_RE.search(url)
        if m2:
            dt = _parse_date_str(f"{m2.group(1)}-{m2.group(2)}-{m2.group(3)}")
            if dt:
                return dt

    return None


def _extract_date_from_card(tag) -> Optional[datetime]:
    """Look for a date in the article card surrounding the <a> tag.

    Checks (in order): <time datetime>, CSS class date elements, embedded ISO JSON.
    Searches the <a> itself, its parent, and grandparent.
    """
    candidates = [tag]
    if tag.parent:
        candidates.append(tag.parent)
        if tag.parent.parent:
            candidates.append(tag.parent.parent)

    for node in candidates:
        # <time datetime=...>
        time_el = node.find("time")
        if time_el:
            dt_attr = time_el.get("datetime", "")
            if dt_attr:
                dt = _parse_date_str(dt_attr)
                if dt:
                    return dt

        # CSS class-based date text
        for el in node.find_all(class_=_DATE_CLASS_RE):
            txt = el.get_text(strip=True)
            dt = _parse_date_str(txt) or _parse_yyyymmdd(txt)
            if dt:
                return dt

    return None


def _build_url_date_map(html: str) -> dict[str, datetime]:
    """Build a URL → date mapping from Next.js __NEXT_DATA__ / RSC payloads.

    Handles two patterns:
    - Standard __NEXT_DATA__ JSON: recursively walk for objects with a url-like
      field and a date-like field in the same dict.
    - RSC / inline JSON strings: scan raw HTML for adjacent "remoteLink"/"url"/"href"
      and "date" pairs within 300 chars of each other.
    """
    result: dict[str, datetime] = {}

    # Strategy A: __NEXT_DATA__ recursive walk
    soup = BeautifulSoup(html, "lxml")
    nd = soup.find("script", id="__NEXT_DATA__")
    if nd:
        try:
            data = json.loads(nd.string or "")
            _walk_json_for_url_dates(data, result)
        except Exception:
            pass

    # Strategy B: RSC inline payload (handles both normal and escaped JSON quotes)
    # Unescape \\" → " so the regex can work uniformly
    unescaped = html.replace('\\"', '"')
    _URL_NEAR_DATE_RE = re.compile(
        r'"(?:remoteLink|url|href|link)"\s*:\s*"(https?://[^"]{10,})"'
        r'.{0,400}?"date"\s*:\s*"(20\d{2}-\d{2}-\d{2}[^"]*)"',
        re.DOTALL,
    )
    _DATE_NEAR_URL_RE = re.compile(
        r'"date"\s*:\s*"(20\d{2}-\d{2}-\d{2}[^"]*)".{0,400}?'
        r'"(?:remoteLink|url|href|link)"\s*:\s*"(https?://[^"]{10,})"',
        re.DOTALL,
    )
    for m in _URL_NEAR_DATE_RE.finditer(unescaped):
        dt = _parse_date_str(m.group(2))
        if dt:
            result[m.group(1)] = dt
    for m in _DATE_NEAR_URL_RE.finditer(unescaped):
        dt = _parse_date_str(m.group(1))
        if dt:
            result[m.group(2)] = dt

    return result


def _walk_json_for_url_dates(obj, result: dict, _depth: int = 0):
    if _depth > 10:
        return
    if isinstance(obj, dict):
        url = obj.get("url") or obj.get("href") or obj.get("link") or obj.get("remoteLink")
        date_val = obj.get("date") or obj.get("datePublished") or obj.get("publishedAt") or obj.get("createdAt")
        if url and date_val and isinstance(url, str) and url.startswith("http"):
            dt = _parse_date_str(str(date_val))
            if dt:
                result[url] = dt
        for v in obj.values():
            _walk_json_for_url_dates(v, result, _depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            _walk_json_for_url_dates(item, result, _depth + 1)


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
        url_date_map = _build_url_date_map(html)

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

            published_at = _extract_date_from_card(tag) or url_date_map.get(full_url)
            items.append(RawItem(
                source_id=self.source_id,
                source_name=self.source_name,
                url=full_url,
                title=title[:200],
                content="",
                published_at=published_at,
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
                if item.published_at is None:
                    item.published_at = _extract_published_date(resp.text, item.url)
            except Exception as e:
                logger.debug(f"[{self.source_name}] content fetch failed for {item.url}: {e}")
