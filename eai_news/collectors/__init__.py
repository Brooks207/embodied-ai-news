import asyncio
from pathlib import Path

import yaml
from loguru import logger

from ..config.settings import settings
from .base import BaseCollector, CollectorResult
from .rss_collector import RSSCollector
from .twitter_collector import TwitterCollector
from .youtube_collector import YouTubeCollector
from .weibo_collector import WeiboCollector
from .web_crawler import WebCrawler
from .playwright_crawler import PlaywrightCrawler
from .jiqizhixin_collector import JiqizhixinCollector
from .galbot_collector import GalbotCollector
from ..models import RawItem

_SOURCES_PATH = Path(__file__).parent.parent / "config" / "sources.yaml"
_MAX_CONSECUTIVE_FAILURES = 3
_consecutive_failures: dict[str, int] = {}


def build_collectors() -> list[tuple[BaseCollector, int, int]]:
    with open(_SOURCES_PATH) as f:
        cfg = yaml.safe_load(f)

    collectors: list[tuple[BaseCollector, int, int]] = []

    for src in cfg.get("rss", []):
        collectors.append((RSSCollector(src["id"], src["name"], src["url"]), src.get("tier", 3), src.get("importance", 3)))

    if settings.twitter_configured:
        for src in cfg.get("twitter", []):
            collectors.append((TwitterCollector(
                src["id"], src["name"], src["handle"], settings.twitter_bearer_token,
            ), src.get("tier", 1), src.get("importance", 3)))
    else:
        logger.warning("Twitter bearer token not set — skipping Twitter collectors")

    if settings.youtube_configured:
        for src in cfg.get("youtube", []):
            if "UCxxxxxx" not in src.get("channel_id", ""):
                collectors.append((YouTubeCollector(
                    src["id"], src["name"], src["channel_id"], settings.youtube_api_key,
                ), src.get("tier", 1), src.get("importance", 3)))
    else:
        logger.warning("YouTube API key not set — skipping YouTube collectors")

    for src in cfg.get("weibo", []):
        collectors.append((WeiboCollector(
            src["id"], src["name"], src["username"], settings.weibo_cookie or "",
        ), src.get("tier", 1), src.get("importance", 3)))

    for src in cfg.get("web", []):
        if src.get("disabled"):
            continue
        collector_type = src.get("collector")
        if collector_type == "jiqizhixin":
            collectors.append((JiqizhixinCollector(), src.get("tier", 2), src.get("importance", 3)))
        elif collector_type == "galbot":
            collectors.append((GalbotCollector(), src.get("tier", 1), src.get("importance", 4)))
        elif src.get("use_browser"):
            collectors.append((PlaywrightCrawler(
                src["id"], src["name"], src["url"],
                article_selector=src.get("article_selector", "a[href]"),
                allow_external=src.get("allow_external", False),
                wait_selector=src.get("wait_selector"),
                full_browser=src.get("full_browser", False),
            ), src.get("tier", 2), src.get("importance", 3)))
        else:
            collectors.append((WebCrawler(
                src["id"], src["name"], src["url"],
                article_selector=src.get("article_selector", "a[href]"),
                allow_external=src.get("allow_external", False),
            ), src.get("tier", 3), src.get("importance", 3)))

    logger.info(f"Built {len(collectors)} collectors")
    return collectors


async def run_all_collectors() -> list[RawItem]:
    collector_pairs = build_collectors()

    active: list[tuple[BaseCollector, int, int]] = []
    skipped: list[str] = []
    for c, tier, importance in collector_pairs:
        if _consecutive_failures.get(c.source_id, 0) >= _MAX_CONSECUTIVE_FAILURES:
            skipped.append(c.source_name)
        else:
            active.append((c, tier, importance))

    if skipped:
        logger.warning(f"Circuit-broken sources skipped ({len(skipped)}): {', '.join(skipped)}")

    tasks = [c.safe_fetch() for c, _, _ in active]
    results: list[CollectorResult] = await asyncio.gather(*tasks)

    all_items: list[RawItem] = []
    failed: list[str] = []

    for result, (_, tier, importance) in zip(results, active):
        if result.ok:
            _consecutive_failures[result.source_id] = 0
            for item in result.items:
                item.raw_metadata["tier"] = tier
                item.raw_metadata["importance"] = importance
            all_items.extend(result.items)
        else:
            count = _consecutive_failures.get(result.source_id, 0) + 1
            _consecutive_failures[result.source_id] = count
            failed.append(f"{result.source_name} ({result.error})")
            if count >= _MAX_CONSECUTIVE_FAILURES:
                logger.error(
                    f"[{result.source_name}] circuit open after {count} consecutive failures"
                )

    if failed:
        logger.warning(f"Failed sources ({len(failed)}): {'; '.join(failed)}")

    ok_count = len(active) - len(failed)
    logger.info(
        f"Total raw items: {len(all_items)} from {ok_count}/{len(active)} active sources"
        + (f" | {len(skipped)} circuit-broken" if skipped else "")
    )
    return all_items
