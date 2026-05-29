import json
from datetime import datetime, timedelta
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
            try:
                await db.execute("ALTER TABLE news_items ADD COLUMN importance REAL NOT NULL DEFAULT 0")
                await db.commit()
                logger.info("Database migrated: added importance column")
            except Exception:
                pass  # column already exists
        logger.info(f"Database initialised at {self.db_path}")

    async def get_existing_raw_ids(self, since_days: int = 30) -> set[str]:
        cutoff = (datetime.utcnow() - timedelta(days=since_days)).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT id FROM raw_items WHERE fetched_at >= ?", (cutoff,)
            ) as cur:
                rows = await cur.fetchall()
        return {r[0] for r in rows}

    async def save_raw_item(self, item: RawItem):
        await self.save_raw_items_batch([item])

    async def save_raw_items_batch(self, items: list[RawItem]):
        if not items:
            return
        rows = [
            (
                item.id, item.source_id, item.source_name, item.url, item.title,
                item.content,
                item.published_at.isoformat() if item.published_at else None,
                item.fetched_at.isoformat(),
                item.status.value,
                json.dumps(item.raw_metadata),
            )
            for item in items
        ]
        async with aiosqlite.connect(self.db_path) as db:
            await db.executemany(
                """INSERT OR IGNORE INTO raw_items
                   (id, source_id, source_name, url, title, content, published_at,
                    fetched_at, status, raw_metadata)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                rows,
            )
            await db.commit()
        logger.debug(f"Batch saved {len(items)} raw items")

    async def save_news_item(self, item: NewsItem):
        await self.save_news_items_batch([item])

    async def save_news_items_batch(self, items: list[NewsItem]):
        if not items:
            return
        rows = [
            (
                item.id, item.raw_item_id, item.source_name, item.url, item.title,
                item.title_zh, item.summary, item.category.value,
                item.relevance_score, item.importance, json.dumps(item.tags),
                item.published_at.isoformat() if item.published_at else None,
                item.created_at.isoformat(),
            )
            for item in items
        ]
        async with aiosqlite.connect(self.db_path) as db:
            await db.executemany(
                """INSERT OR IGNORE INTO news_items
                   (id, raw_item_id, source_name, url, title, title_zh, summary,
                    category, relevance_score, importance, tags, published_at, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                rows,
            )
            await db.commit()
        logger.debug(f"Batch saved {len(items)} news items")

    async def update_news_item_llm_fields(self, item_id: str, title_zh: str | None, summary: str, tags: list) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE news_items SET title_zh=?, summary=?, tags=? WHERE id=?",
                (title_zh, summary, json.dumps(tags), item_id),
            )
            await db.commit()

    async def update_news_item_importance(self, item_id: str, importance: float) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE news_items SET importance=? WHERE id=?",
                (importance, item_id),
            )
            await db.commit()

    async def get_news_items_by_ids(self, ids: list[str]) -> list[dict]:
        placeholders = ",".join("?" * len(ids))
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                f"SELECT * FROM news_items WHERE id IN ({placeholders})", ids
            ) as cur:
                rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def get_unprocessed_news(self, limit: int = 100) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM news_items WHERE title_zh IS NULL ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ) as cur:
                rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def get_recent_news_titles(self, since_days: int = 3) -> list[tuple[str, "datetime | None"]]:
        """Return (title, published_at) for accepted news_items from the last N days."""
        cutoff = (datetime.utcnow() - timedelta(days=since_days)).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT title, published_at FROM news_items WHERE created_at >= ?",
                (cutoff,),
            ) as cur:
                rows = await cur.fetchall()
        result = []
        for title, pub_str in rows:
            pub = None
            if pub_str:
                try:
                    pub = datetime.fromisoformat(pub_str)
                except Exception:
                    pass
            result.append((title, pub))
        return result

    async def get_recent_news_titles_zh(self, since_days: int = 3) -> list[tuple[str, "datetime | None"]]:
        """Return (title_zh, published_at) for accepted news_items with a Chinese title."""
        cutoff = (datetime.utcnow() - timedelta(days=since_days)).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT title_zh, published_at FROM news_items WHERE created_at >= ? AND title_zh IS NOT NULL",
                (cutoff,),
            ) as cur:
                rows = await cur.fetchall()
        result = []
        for title_zh, pub_str in rows:
            pub = None
            if pub_str:
                try:
                    pub = datetime.fromisoformat(pub_str)
                except Exception:
                    pass
            result.append((title_zh, pub))
        return result

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
