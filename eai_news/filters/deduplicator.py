import re
from datetime import datetime
from difflib import SequenceMatcher

from ..models import RawItem

_SIMILARITY_THRESHOLD = 0.70
_TIME_WINDOW_SECONDS = 48 * 3600


def _normalize(title: str) -> str:
    title = title.lower()
    title = re.sub(r"[^\w\s一-鿿]", " ", title)
    return re.sub(r"\s+", " ", title).strip()


def _similar(a: str, b: str) -> bool:
    return SequenceMatcher(None, a, b).ratio() >= _SIMILARITY_THRESHOLD


def _within_window(t1: datetime | None, t2: datetime | None) -> bool:
    if t1 is None or t2 is None:
        return True  # 时间未知时保守处理，认为在窗口内
    return abs((t1 - t2).total_seconds()) <= _TIME_WINDOW_SECONDS


class Deduplicator:
    def __init__(self, existing_ids: set[str]):
        self._existing = existing_ids

    def filter(self, items: list[RawItem]) -> list[RawItem]:
        # Step 1: URL 去重（跨批次）
        url_unique = [i for i in items if i.id not in self._existing]

        # Step 2: 批次内标题模糊去重，tier 低（一手）优先
        # 先按 tier 排序，tier=1 排最前，保证一手来源优先保留
        url_unique.sort(key=lambda x: x.raw_metadata.get("tier", 3))

        result: list[RawItem] = []
        accepted: list[tuple[str, datetime | None]] = []  # (normalized_title, published_at)

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
