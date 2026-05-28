"""
JiqizhixinCollector — 机器之心专用采集器。

机器之心首页是 CSR 页面，文章列表通过 AJAX 请求加载：
  GET /api/article_library/articles.json?sort=time&page=1&per=12

Playwright 加载首页时浏览器会自动发起该请求，我们拦截响应体即可，
无需解析 DOM，也无需登录（首页公开内容）。

返回的 JSON 结构（简化）：
{
  "articles": [
    {
      "id": 123,
      "title": "...",
      "slug": "2026-05-28-15",
      "publishedAt": "2026-05-28T14:00:00.000+08:00",
      "content": "...",          # 正文（有时较短）
      "coverImageUrl": "...",
      "category": {...},
      "tagList": [...]
    },
    ...
  ]
}

文章 URL = https://www.jiqizhixin.com/articles/{slug}
"""
import asyncio
import json

from loguru import logger

from ..models import RawItem
from .base import BaseCollector
from .playwright_crawler import _PAGE_SEM, _get_browser

_BASE_URL = "https://www.jiqizhixin.com"
_API_PATH = "article_library/articles.json"     # 匹配时用 in 检查


class JiqizhixinCollector(BaseCollector):
    """机器之心首页文章采集器（Playwright 响应拦截）。"""

    source_id   = "web_jiqizhixin"
    source_name = "机器之心"

    def __init__(self):
        self.index_url = _BASE_URL

    async def fetch(self) -> list[RawItem]:
        browser = await _get_browser()

        captured: list[dict] = []   # 拦截到的原始 article 对象

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

                # 注册响应拦截器
                async def handle_response(response):
                    if _API_PATH in response.url and response.status == 200:
                        try:
                            data = await response.json()
                            arts = data.get("articles", [])
                            captured.extend(arts)
                            logger.debug(
                                f"[机器之心] 拦截到 API 响应，共 {len(arts)} 篇文章"
                            )
                        except Exception as e:
                            logger.warning(f"[机器之心] 解析 API 响应失败: {e}")

                page.on("response", handle_response)

                await page.goto(
                    self.index_url,
                    wait_until="networkidle",
                    timeout=30_000,
                )
                # networkidle 后给一点额外时间确保异步处理完成
                await asyncio.sleep(1)

            except Exception as e:
                logger.warning(f"[机器之心] Playwright 页面加载失败: {e}")
                return []
            finally:
                await context.close()

        if not captured:
            logger.warning("[机器之心] 未拦截到任何文章，可能 API 路径已变更")
            return []

        logger.info(f"[机器之心] 共拦截到 {len(captured)} 篇文章")
        items: list[RawItem] = []

        for art in captured:
            slug = art.get("slug") or str(art.get("id", ""))
            if not slug:
                continue

            title = art.get("title", "").strip()
            if not title:
                continue

            url = f"{_BASE_URL}/articles/{slug}"

            # 尝试解析发布时间
            # 1) 优先读 API 字段（Rails ISO 8601）
            # 2) Fallback：从 slug 格式 YYYY-MM-DD-N 提取日期
            published_at = None
            from datetime import datetime, timezone, timedelta
            _CST = timezone(timedelta(hours=8))
            for _field in ("publishedAt", "published_at", "createdAt", "created_at"):
                pub_str = art.get(_field)
                if pub_str:
                    try:
                        published_at = datetime.fromisoformat(str(pub_str))
                        break
                    except Exception:
                        pass
            if published_at is None and isinstance(slug, str):
                # slug: "2026-05-28-15" or "2026-05-28-some-title"
                import re
                m = re.match(r'^(\d{4}-\d{2}-\d{2})', slug)
                if m:
                    try:
                        published_at = datetime(
                            *map(int, m.group(1).split("-")),
                            tzinfo=_CST,
                        )
                    except Exception:
                        pass

            # content 字段有时包含完整正文，有时只有摘要，直接使用
            content = art.get("content") or art.get("summary") or ""

            # category / tags 可能是字符串或字典，兼容两种格式
            cat = art.get("category", "")
            if isinstance(cat, dict):
                cat = cat.get("name", "")

            tags_raw = art.get("tagList", [])
            tags = [
                (t.get("name", "") if isinstance(t, dict) else str(t))
                for t in tags_raw
            ]

            items.append(
                RawItem(
                    source_id=self.source_id,
                    source_name=self.source_name,
                    url=url,
                    title=title[:200],
                    content=content[:1000],
                    published_at=published_at,
                    raw_metadata={
                        "slug": slug,
                        "category": str(cat),
                        "tags": tags,
                        "cover": art.get("coverImageUrl", ""),
                    },
                )
            )

        return items
