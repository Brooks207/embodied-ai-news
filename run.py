#!/usr/bin/env python3
"""
Entry point for EAI News Automation Platform

Usage:
  python run.py                  # Start the scheduler (runs indefinitely)
  python run.py --once           # Run a single collection cycle and exit
  python run.py --process-only   # LLM-process unprocessed DB items and exit
  python run.py --setup-feishu   # 一次性初始化飞书多维表格字段（建完后不再需要）
"""
import asyncio
import sys

from loguru import logger


def main():
    once = "--once" in sys.argv
    setup_feishu = "--setup-feishu" in sys.argv
    process_only = "--process-only" in sys.argv

    if setup_feishu:
        asyncio.run(_setup_feishu())
        return

    logger.add(
        "eai_news/data/logs/eai_news_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        level="INFO",
        encoding="utf-8",
    )

    if process_only:
        logger.info("Processing unprocessed items with LLM...")
        asyncio.run(_process_only())
    elif once:
        logger.info("Running single collection cycle...")
        from eai_news.scheduler import run_once
        asyncio.run(run_once())
    else:
        logger.info("Starting EAI News scheduler...")
        asyncio.run(_run_scheduler())


async def _process_only():
    from eai_news.config.settings import settings
    from eai_news.storage import get_db
    from eai_news.models import NewsItem, NewsCategory
    from eai_news.processors.llm_processor import LLMProcessor
    from datetime import datetime

    if not settings.claude_configured:
        logger.error("ANTHROPIC_API_KEY not set — cannot run LLM processing")
        return

    db = get_db()
    await db.init()
    rows = await db.get_unprocessed_news(limit=200)
    if not rows:
        logger.info("No unprocessed items found")
        return

    logger.info(f"Found {len(rows)} unprocessed items")
    items = [
        NewsItem(
            id=r["id"],
            raw_item_id=r["raw_item_id"],
            source_name=r["source_name"],
            url=r["url"],
            title=r["title"],
            title_zh=r.get("title_zh"),
            summary=r.get("summary", ""),
            category=NewsCategory(r["category"]),
            relevance_score=r.get("relevance_score", 0.0),
            tags=[],
            published_at=datetime.fromisoformat(r["published_at"]) if r.get("published_at") else None,
        )
        for r in rows
    ]

    processor = LLMProcessor(api_key=settings.anthropic_api_key)
    processed = await processor.process(items)

    updated = 0
    for item in processed:
        if item.title_zh:
            await db.update_news_item_llm_fields(item.id, item.title_zh, item.summary, item.tags)
            updated += 1

    logger.info(f"Updated {updated}/{len(processed)} items with LLM fields")


async def _setup_feishu():
    from eai_news.config.settings import settings
    from eai_news.storage.feishu_table import FeishuTableStorage
    storage = FeishuTableStorage(
        app_id=settings.feishu_app_id,
        app_secret=settings.feishu_app_secret,
        app_token=settings.feishu_bitable_app_token,
        table_id=settings.feishu_table_id,
    )
    await storage.ensure_fields()
    logger.info("飞书多维表格字段初始化完成，后续无需再次运行此命令")


async def _run_scheduler():
    from eai_news.storage import get_db
    from eai_news.scheduler import build_scheduler, run_collection

    db = get_db()
    await db.init()

    # Run once immediately on startup
    await run_collection()

    scheduler = build_scheduler()
    scheduler.start()
    logger.info("Scheduler started. Press Ctrl+C to stop.")

    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")
        scheduler.shutdown()
        from eai_news.collectors.playwright_crawler import close_browser
        await close_browser()


if __name__ == "__main__":
    main()
