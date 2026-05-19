"""
飞书多维表格存储
正常运行时直接写入，不做字段检查。
建表头只需跑一次：python run.py --setup-feishu
"""
import time
from datetime import datetime

import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from ..models import NewsItem, CATEGORY_LABELS_ZH

FEISHU_BASE = "https://open.feishu.cn/open-apis"


class FeishuTableStorage:
    def __init__(self, app_id: str, app_secret: str, app_token: str, table_id: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.app_token = app_token
        self.table_id = table_id
        self._token: str | None = None
        self._token_expires: float = 0

    async def _get_token(self) -> str:
        if self._token and time.time() < self._token_expires - 60:
            return self._token
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{FEISHU_BASE}/auth/v3/tenant_access_token/internal",
                json={"app_id": self.app_id, "app_secret": self.app_secret},
            )
            resp.raise_for_status()
            data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Feishu auth failed: {data.get('msg')}")
        self._token = data["tenant_access_token"]
        self._token_expires = time.time() + data.get("expire", 7200)
        return self._token

    def _build_record(self, item: NewsItem) -> dict:
        ts_ms = None
        if item.published_at:
            ts_ms = int(item.published_at.timestamp() * 1000)
        elif item.created_at:
            ts_ms = int(item.created_at.timestamp() * 1000)

        category_label = CATEGORY_LABELS_ZH.get(item.category, "其他")
        title_display = item.title_zh or item.title

        fields: dict = {
            "发布者": item.source_name,
            "新闻链接": {"link": item.url, "text": item.url},
            "中文标题": title_display,
            "分类": category_label,
            "相关性评分": item.relevance_score,
        }
        if ts_ms:
            fields["时间"] = ts_ms
        return {"fields": fields}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def save_news_item(self, item: NewsItem):
        token = await self._get_token()
        record = self._build_record(item)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{FEISHU_BASE}/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=record,
            )
            resp.raise_for_status()
            data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Feishu save failed: {data.get('msg')} | item={item.url}")
        logger.debug(f"[Feishu] saved: {item.title[:60]}")

    async def ensure_fields(self):
        """首次运行时自动创建所需字段。"""
        token = await self._get_token()
        fields_to_create = [
            ("时间", 5, None),
            ("新闻链接", 15, None),
            ("发布者", 1, None),
            ("中文标题", 1, None),
            ("分类", 3, {"options": [
                {"name": "融资"}, {"name": "产品"}, {"name": "落地"},
                {"name": "人才"}, {"name": "供应链"}, {"name": "政策"}, {"name": "其他"},
            ]}),
            ("相关性评分", 2, None),
        ]
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{FEISHU_BASE}/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/fields",
                headers={"Authorization": f"Bearer {token}"},
            )
            existing = {f["field_name"] for f in resp.json().get("data", {}).get("items", [])}
            for name, ftype, prop in fields_to_create:
                if name in existing:
                    continue
                body: dict = {"field_name": name, "type": ftype}
                if prop:
                    body["property"] = prop
                await client.post(
                    f"{FEISHU_BASE}/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/fields",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json=body,
                )
                logger.info(f"[Feishu] created field: {name}")

    async def save_batch(self, items: list[NewsItem]):
        ok = fail = 0
        for item in items:
            try:
                await self.save_news_item(item)
                ok += 1
            except Exception as e:
                logger.warning(f"[Feishu] failed to save {item.url}: {e}")
                fail += 1
        logger.info(f"[Feishu] batch done — ok={ok}, fail={fail}")
