#!/usr/bin/env python3
"""
Entry point for EAI News Automation Platform

Usage:
  python run.py                # Start the scheduler (runs indefinitely)
  python run.py --once         # Run a single collection cycle and exit
  python run.py --setup-feishu # 一次性初始化飞书多维表格字段（建完后不再需要）
"""
import asyncio
import sys

from loguru import logger


def main():
    once = "--once" in sys.argv
    setup_feishu = "--setup-feishu" in sys.argv

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

    if once:
        logger.info("Running single collection cycle...")
        from eai_news.scheduler import run_once
        asyncio.run(run_once())
    else:
        logger.info("Starting EAI News scheduler...")
        asyncio.run(_run_scheduler())


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


if __name__ == "__main__":
    main()
