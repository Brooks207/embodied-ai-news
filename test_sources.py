#!/usr/bin/env python3
"""
测试所有 sources 是否可以正常拉取数据。
只测试 rss 和 web 两类（twitter/youtube/weibo 需要 API，暂跳过）。

Usage:
  python test_sources.py
  python test_sources.py --rss-only
  python test_sources.py --web-only
"""
import asyncio
import sys
import time
from pathlib import Path

import yaml
from loguru import logger

# 移除默认 stderr handler，用自定义格式
logger.remove()
logger.add(sys.stderr, format="<level>{message}</level>", level="INFO")

ROOT = Path(__file__).parent
SOURCES_YAML = ROOT / "eai_news" / "config" / "sources.yaml"

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"


def fmt(color, text): return f"{color}{text}{RESET}"


async def test_rss(source: dict) -> dict:
    from eai_news.collectors.rss_collector import RSSCollector
    name = source["name"]
    sid  = source["id"]
    url  = source["url"]
    collector = RSSCollector(sid, name, url)
    t0 = time.monotonic()
    try:
        items = await collector.fetch()
        elapsed = time.monotonic() - t0
        if items:
            return {"id": sid, "name": name, "status": "ok",
                    "count": len(items), "elapsed": elapsed,
                    "sample": items[0].title[:60]}
        else:
            return {"id": sid, "name": name, "status": "empty",
                    "count": 0, "elapsed": elapsed, "sample": ""}
    except Exception as e:
        elapsed = time.monotonic() - t0
        return {"id": sid, "name": name, "status": "error",
                "count": 0, "elapsed": elapsed, "sample": str(e)[:80]}


async def test_web(source: dict) -> dict:
    if source.get("use_browser"):
        from eai_news.collectors.playwright_crawler import PlaywrightCrawler
        name     = source["name"]
        sid      = source["id"]
        url      = source["url"]
        selector = source.get("article_selector", "a[href]")
        allow_ext = source.get("allow_external", False)
        wait_sel  = source.get("wait_selector")
        collector = PlaywrightCrawler(sid, name, url, selector, allow_ext, wait_sel)
    else:
        from eai_news.collectors.web_crawler import WebCrawler
        name     = source["name"]
        sid      = source["id"]
        url      = source["url"]
        selector = source.get("article_selector", "a[href]")
        allow_ext = source.get("allow_external", False)
        collector = WebCrawler(sid, name, url, selector, allow_ext)
    t0 = time.monotonic()
    try:
        items = await collector.fetch()
        elapsed = time.monotonic() - t0
        if items:
            return {"id": sid, "name": name, "status": "ok",
                    "count": len(items), "elapsed": elapsed,
                    "sample": items[0].title[:60]}
        else:
            return {"id": sid, "name": name, "status": "empty",
                    "count": 0, "elapsed": elapsed, "sample": ""}
    except Exception as e:
        elapsed = time.monotonic() - t0
        return {"id": sid, "name": name, "status": "error",
                "count": 0, "elapsed": elapsed, "sample": str(e)[:80]}


def print_results(category: str, results: list[dict]):
    print(f"\n{BOLD}{CYAN}{'─'*70}{RESET}")
    print(f"{BOLD}{CYAN}  {category}{RESET}")
    print(f"{BOLD}{CYAN}{'─'*70}{RESET}")
    col_w = 34
    print(f"  {'Name':<{col_w}} {'Status':<8} {'Items':>5}  {'Time':>5}s  Sample")
    print(f"  {'─'*col_w} {'─'*7} {'─'*5}  {'─'*6}  {'─'*30}")
    ok = empty = err = 0
    for r in results:
        status = r["status"]
        if status == "ok":
            s = fmt(GREEN, f"{'✓ ok':<8}")
            ok += 1
        elif status == "empty":
            s = fmt(YELLOW, f"{'⚠ empty':<8}")
            empty += 1
        else:
            s = fmt(RED, f"{'✗ error':<8}")
            err += 1
        name_trunc = r["name"][:col_w]
        print(f"  {name_trunc:<{col_w}} {s} {r['count']:>5}  {r['elapsed']:>6.1f}  {r['sample']}")
    print(f"\n  {fmt(GREEN,'OK')}: {ok}  {fmt(YELLOW,'Empty')}: {empty}  {fmt(RED,'Error')}: {err}  Total: {len(results)}")


async def main():
    rss_only = "--rss-only" in sys.argv
    web_only = "--web-only" in sys.argv

    with open(SOURCES_YAML, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    rss_sources = config.get("rss", [])
    web_sources = [s for s in config.get("web", []) if not s.get("disabled")]

    print(f"\n{BOLD}EAI News — Source Health Check{RESET}")
    print(f"RSS sources: {len(rss_sources)}  |  Web sources (enabled): {len(web_sources)}")

    # ── RSS ──────────────────────────────────────────────────────────
    if not web_only:
        print(f"\n{fmt(CYAN, '▶ Testing RSS sources...')}")
        rss_tasks = [test_rss(s) for s in rss_sources]
        rss_results = await asyncio.gather(*rss_tasks)
        print_results("RSS Feeds", list(rss_results))

    # ── Web ──────────────────────────────────────────────────────────
    if not rss_only:
        print(f"\n{fmt(CYAN, '▶ Testing Web crawler sources (concurrency=5)...')}")
        sem = asyncio.Semaphore(5)

        async def bounded_web(s):
            async with sem:
                return await test_web(s)

        web_tasks = [bounded_web(s) for s in web_sources]
        web_results = await asyncio.gather(*web_tasks)
        print_results("Web Crawlers", list(web_results))

    print(f"\n{BOLD}Done.{RESET}\n")

    # 关闭 Playwright 浏览器（如果启动过的话）
    from eai_news.collectors.playwright_crawler import close_browser
    await close_browser()


if __name__ == "__main__":
    asyncio.run(main())
