import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from .config.settings import settings
from .collectors import run_all_collectors
from .filters.pipeline import FilterPipeline
from .storage import get_db, save_batch


async def run_collection():
    logger.info("=== Collection cycle started ===")
    try:
        # 1. Fetch raw items
        raw_items = await run_all_collectors()

        # 2. Get existing IDs for dedup
        db = get_db()
        existing_ids = await db.get_existing_raw_ids()

        # 3. Save all raw items (for audit trail)
        for item in raw_items:
            await db.save_raw_item(item)

        # 4. Filter
        pipeline = FilterPipeline(existing_ids=existing_ids)
        news_items = pipeline.process(raw_items)

        # 5. Save accepted items
        await save_batch(news_items)

        logger.info(f"=== Collection done: {len(news_items)} new items saved ===")
    except Exception as e:
        logger.error(f"Collection cycle failed: {e}", exc_info=True)


def build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

    scheduler.add_job(
        run_collection,
        IntervalTrigger(hours=settings.collect_interval_hours),
        id="collection",
        name="信息采集",
        replace_existing=True,
        misfire_grace_time=300,
    )

    logger.info(
        f"Scheduler configured: collection every {settings.collect_interval_hours}h"
    )
    return scheduler


async def run_once():
    """Run a single collection cycle (for testing / manual trigger)."""
    db = get_db()
    await db.init()
    await run_collection()
