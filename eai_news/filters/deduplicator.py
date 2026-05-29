import re
from datetime import datetime
from difflib import SequenceMatcher

from loguru import logger

from ..models import NewsItem, RawItem

_SIMILARITY_THRESHOLD = 0.45     # 原始标题去重阈值（英文/中文均适用）
_ZH_SIMILARITY_THRESHOLD = 0.45  # title_zh 去重阈值
_TIME_WINDOW_SECONDS = 48 * 3600


def _normalize(title: str) -> str:
    title = title.lower()
    title = re.sub(r"[^\w\s一-鿿]", " ", title)
    return re.sub(r"\s+", " ", title).strip()


def _similar(a: str, b: str, threshold: float = _SIMILARITY_THRESHOLD) -> bool:
    return SequenceMatcher(None, a, b).ratio() >= threshold


def _within_window(t1: datetime | None, t2: datetime | None) -> bool:
    if t1 is None or t2 is None:
        return True  # 时间未知时保守处理，认为在窗口内
    return abs((t1 - t2).total_seconds()) <= _TIME_WINDOW_SECONDS


class Deduplicator:
    def __init__(
        self,
        existing_ids: set[str],
        existing_titles: list[tuple[str, datetime | None]] | None = None,
    ):
        self._existing = existing_ids
        # 预归一化历史标题，用于跨批次去重
        self._existing_titles: list[tuple[str, datetime | None]] = [
            (_normalize(t), pub) for t, pub in (existing_titles or []) if t
        ]

    def filter(self, items: list[RawItem]) -> list[RawItem]:
        # Step 1: URL 去重（跨批次）
        url_unique = [i for i in items if i.id not in self._existing]

        # Step 2: 标题模糊去重——跨批次历史 + 批次内，tier 低（一手）优先
        url_unique.sort(key=lambda x: x.raw_metadata.get("tier", 3))

        result: list[RawItem] = []
        # 用历史已接收标题作为初始种子，实现跨批次去重
        accepted: list[tuple[str, datetime | None]] = list(self._existing_titles)

        for item in url_unique:
            norm = _normalize(item.title)
            is_dup = any(
                _within_window(item.published_at, acc_time) and _similar(norm, acc_norm)
                for acc_norm, acc_time in accepted
            )
            if not is_dup:
                result.append(item)
                accepted.append((norm, item.published_at))

        return result


def dedup_by_title_zh(
    items: list[NewsItem],
    existing_zh: list[tuple[str, datetime | None]],
) -> list[NewsItem]:
    """LLM 处理后用 title_zh 做跨语言跨批次去重。"""
    accepted: list[tuple[str, datetime | None]] = [
        (_normalize(zh), pub) for zh, pub in existing_zh if zh
    ]
    result: list[NewsItem] = []
    for item in items:
        key = item.title_zh or item.title
        if not key:
            result.append(item)
            continue
        norm = _normalize(key)
        is_dup = any(
            _within_window(item.published_at, acc_time)
            and _similar(norm, acc_norm, _ZH_SIMILARITY_THRESHOLD)
            for acc_norm, acc_time in accepted
        )
        if is_dup:
            logger.info(f"title_zh dedup dropped: [{item.source_name}] {key[:60]}")
        else:
            result.append(item)
            accepted.append((norm, item.published_at))
    dropped = len(items) - len(result)
    if dropped:
        logger.info(f"title_zh dedup: {dropped} cross-source duplicate(s) removed")
    return result
