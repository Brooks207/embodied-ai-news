from datetime import datetime, timezone

import httpx
from loguru import logger

from ..models import RawItem
from .base import BaseCollector

# 微博移动端非官方 API，可能随时失效
WEIBO_MOBILE_API = "https://m.weibo.cn/api/container/getIndex"


class WeiboCollector(BaseCollector):
    """Fetch recent posts from a Weibo account via mobile API."""

    def __init__(
        self,
        source_id: str,
        source_name: str,
        username: str,
        cookie: str = "",
    ):
        self.source_id = source_id
        self.source_name = source_name
        self.username = username
        self.cookie = cookie
        self._uid_cache: dict[str, str] = {}

    async def _resolve_uid(self, client: httpx.AsyncClient) -> str | None:
        """Resolve username to Weibo UID."""
        if self.username in self._uid_cache:
            return self._uid_cache[self.username]
        try:
            resp = await client.get(
                f"https://weibo.com/{self.username}",
                headers=self._headers(),
                follow_redirects=True,
            )
            # Extract uid from $CONFIG.oid in the page source
            for line in resp.text.splitlines():
                if "$CONFIG['oid']" in line:
                    uid = line.split("'")[3]
                    self._uid_cache[self.username] = uid
                    return uid
        except Exception as e:
            logger.debug(f"[Weibo] uid resolve failed for {self.username}: {e}")
        return None

    def _headers(self) -> dict:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/20A362 "
                "MicroMessenger/8.0.0"
            ),
            "Referer": "https://m.weibo.cn/",
        }
        if self.cookie:
            headers["Cookie"] = self.cookie
        return headers

    async def fetch(self) -> list[RawItem]:
        async with httpx.AsyncClient(timeout=20) as client:
            uid = await self._resolve_uid(client)
            if not uid:
                logger.warning(f"[Weibo] could not resolve UID for @{self.username}")
                return []

            resp = await client.get(
                WEIBO_MOBILE_API,
                params={"uid": uid, "type": "uid", "value": uid, "containerid": f"107603{uid}"},
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        cards = data.get("data", {}).get("cards", [])
        items = []
        for card in cards:
            mblog = card.get("mblog", {})
            if not mblog:
                continue
            mid = mblog.get("id", "")
            text = mblog.get("text", "")
            raw_text = mblog.get("raw_text", text)
            created_at_str = mblog.get("created_at", "")
            url = f"https://weibo.com/{uid}/{mid}"

            published_at = None
            try:
                published_at = datetime.strptime(
                    created_at_str, "%a %b %d %H:%M:%S %z %Y"
                )
            except Exception:
                pass

            # Strip HTML tags from text
            import re
            clean_text = re.sub(r"<[^>]+>", "", raw_text or text).strip()

            items.append(RawItem(
                source_id=self.source_id,
                source_name=self.source_name,
                url=url,
                title=clean_text[:80],
                content=clean_text,
                published_at=published_at,
                raw_metadata={"mid": mid, "uid": uid},
            ))
        return items
