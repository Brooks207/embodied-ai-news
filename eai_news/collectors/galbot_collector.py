"""
GalbotCollector — 银河通用新闻采集器。

银河通用官网新闻通过 POST API 直接返回 JSON，无需浏览器：
  POST https://api.galbot.com/api/v1/web/news/list
  Body: {"page": 1, "pageSize": 20}

返回字段（精简）：
  id, title, url, content, publish_time
  url 为外部链接（微信公众号文章 / 媒体报道）
"""
from datetime import datetime

import httpx
from loguru import logger

from ..models import RawItem
from .base import BaseCollector

_API_URL = "https://api.galbot.com/api/v1/web/news/list"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Origin": "https://www.galbot.com",
    "Referer": "https://www.galbot.com/news",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


class GalbotCollector(BaseCollector):
    """银河通用新闻采集器（REST API 直调，无需 Playwright）。"""

    source_id   = "web_galbot"
    source_name = "银河通用"

    def __init__(self, page_size: int = 20):
        self.page_size = page_size

    async def fetch(self) -> list[RawItem]:
        payload = {"page": 1, "pageSize": self.page_size}
        try:
            async with httpx.AsyncClient(
                timeout=15,
                headers=_HEADERS,
                follow_redirects=True,
            ) as client:
                resp = await client.post(_API_URL, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.warning(f"[银河通用] API 请求失败: {e}")
            return []

        if data.get("code") != 200:
            logger.warning(f"[银河通用] API 返回错误: {data.get('msg', data)}")
            return []

        articles = data.get("data", {}).get("list", [])
        if not articles:
            logger.warning("[银河通用] API 返回 0 条文章")
            return []

        logger.info(f"[银河通用] 共获取 {len(articles)} 条新闻")
        items: list[RawItem] = []

        for art in articles:
            url = art.get("url") or art.get("en_url") or ""
            if not url:
                continue

            title = art.get("title", "").strip()
            if not title:
                continue

            content = art.get("content") or art.get("eng_content") or ""

            published_at = None
            if pub_str := art.get("publish_time"):
                try:
                    published_at = datetime.strptime(str(pub_str)[:10], "%Y-%m-%d")
                except Exception:
                    pass

            items.append(
                RawItem(
                    source_id=self.source_id,
                    source_name=self.source_name,
                    url=url,
                    title=title[:200],
                    content=content[:500],
                    published_at=published_at,
                    raw_metadata={
                        "galbot_id": art.get("id"),
                        "eng_title": art.get("eng_title", ""),
                    },
                )
            )

        return items
