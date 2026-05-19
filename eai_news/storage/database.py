import json
from pathlib import Path

import aiosqlite
from loguru import logger

from ..models import RawItem, NewsItem

_SCHEMA_PATH = Path(__file__).parent.parent / "db" / "schema.sql"


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def init(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            schema = _SCHEMA_PATH.read_text()
            await db.executescript(schema)
            await db.commit()
        logger.info(f"Database initialised at {self.db_path}")

    async def get_existing_raw_ids(self) -> set[str]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT id FROM raw_items") as cur:
                rows = await cur.fetchall()
        return {r[0] for r in rows}

    async def save_raw_item(self, item: RawItem):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR IGNORE INTO raw_items
                    (id, source_id, source_name, url, title, content, published_at,
                     fetched_at, status, raw_metadata)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    item.id, item.source_id, item.source_name, item.url, item.title,
                    item.content,
                    item.published_at.isoformat() if item.published_at else None,
                    item.fetched_at.isoformat(),
                    item.status.value,
                    json.dumps(item.raw_metadata),
                ),
            )
            await db.commit()

    async def save_news_item(self, item: NewsItem):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR IGNORE INTO news_items
                    (id, raw_item_id, source_name, url, title, title_zh, summary,
                     category, relevance_score, tags, published_at, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    item.id, item.raw_item_id, item.source_name, item.url, item.title,
                    item.title_zh, item.summary, item.category.value,
                    item.relevance_score, json.dumps(item.tags),
                    item.published_at.isoformat() if item.published_at else None,
                    item.created_at.isoformat(),
                ),
            )
            await db.commit()

    async def get_recent_news(self, limit: int = 50, category: str | None = None) -> list[dict]:
        sql = "SELECT * FROM news_items"
        params: list = []
        if category:
            sql += " WHERE category = ?"
            params.append(category)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql, params) as cur:
                rows = await cur.fetchall()
        return [dict(r) for r in rows]
