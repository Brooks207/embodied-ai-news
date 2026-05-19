from loguru import logger

from ..config.settings import settings
from .database import Database
from .feishu_table import FeishuTableStorage
from .excel_fallback import ExcelStorage
from ..models import NewsItem

_db: Database | None = None
_feishu: FeishuTableStorage | None = None
_excel: ExcelStorage | None = None


def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database(settings.db_path)
    return _db


def get_feishu() -> FeishuTableStorage | None:
    global _feishu
    if _feishu is None and settings.feishu_configured:
        _feishu = FeishuTableStorage(
            settings.feishu_app_id,
            settings.feishu_app_secret,
            settings.feishu_bitable_app_token,
            settings.feishu_table_id,
        )
    return _feishu


def get_excel() -> ExcelStorage:
    global _excel
    if _excel is None:
        _excel = ExcelStorage(settings.excel_path)
    return _excel


async def save_news_item(item: NewsItem):
    """Save to SQLite DB + external table (Feishu or Excel)."""
    db = get_db()
    await db.save_news_item(item)

    backend = settings.storage_backend
    feishu = get_feishu()

    if backend in ("feishu", "both") and feishu:
        try:
            await feishu.save_news_item(item)
            return
        except Exception as e:
            logger.warning(f"Feishu write failed, falling back to Excel: {e}")

    # Excel fallback
    if backend in ("excel", "both") or not feishu:
        get_excel().save_news_item(item)


async def save_batch(items: list[NewsItem]):
    if not items:
        return
    db = get_db()
    await db.save_news_items_batch(items)

    backend = settings.storage_backend
    feishu = get_feishu()

    if backend in ("feishu", "both") and feishu:
        await feishu.save_batch(items)
    else:
        get_excel().save_batch(items)
