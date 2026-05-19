import asyncio
from pathlib import Path

import yaml
from loguru import logger

from ..config.settings import settings
from .base import BaseCollector
from .rss_collector import RSSCollector
from .twitter_collector import TwitterCollector
from .youtube_collector import YouTubeCollector
from .weibo_collector import WeiboCollector
from .web_crawler import WebCrawler
from ..models import RawItem

_SOURCES_PATH = Path(__file__).parent.parent / "config" / "sources.yaml"


def build_collectors() -> list[tuple[BaseCollector, int]]:
    """Returns list of (collector, tier) tuples."""
    with open(_SOURCES_PATH) as f:
        cfg = yaml.safe_load(f)

    collectors: list[tuple[BaseCollector, int]] = []

    for src in cfg.get("rss", []):
        collectors.append((RSSCollector(src["id"], src["name"], src["url"]), src.get("tier", 3)))

    if settings.twitter_configured:
        for src in cfg.get("twitter", []):
            collectors.append((TwitterCollector(
                src["id"], src["name"], src["handle"], settings.twitter_bearer_token,
            ), src.get("tier", 1)))
    else:
        logger.warning("Twitter bearer token not set — skipping Twitter collectors")

    if settings.youtube_configured:
        for src in cfg.get("youtube", []):
            if "UCxxxxxx" not in src.get("channel_id", ""):
                collectors.append((YouTubeCollector(
                    src["id"], src["name"], src["channel_id"], settings.youtube_api_key,
                ), src.get("tier", 1)))
    else:
        logger.warning("YouTube API key not set — skipping YouTube collectors")

    for src in cfg.get("weibo", []):
        collectors.append((WeiboCollector(
            src["id"], src["name"], src["username"], settings.weibo_cookie or "",
        ), src.get("tier", 1)))

    for src in cfg.get("web", []):
        collectors.append((WebCrawler(
            src["id"], src["name"], src["url"],
            article_selector=src.get("article_selector", "a[href]"),
        ), src.get("tier", 3)))

    logger.info(f"Built {len(collectors)} collectors")
    return collectors


async def run_all_collectors() -> list[RawItem]:
    collector_pairs = build_collectors()
    tasks = [c.safe_fetch() for c, _ in collector_pairs]
    results = await asyncio.gather(*tasks)
    all_items: list[RawItem] = []
    for batch, (_, tier) in zip(results, collector_pairs):
        for item in batch:
            item.raw_metadata["tier"] = tier
        all_items.extend(batch)
    logger.info(f"Total raw items fetched: {len(all_items)}")
    return all_items
