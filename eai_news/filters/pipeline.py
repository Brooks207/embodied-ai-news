import uuid
from datetime import datetime, timezone
from loguru import logger

from ..models import RawItem, NewsItem, ItemStatus
from ..config.settings import settings
from .deduplicator import Deduplicator
from .relevance_scorer import RelevanceScorer


def _first_para(text: str, max_chars: int = 200) -> str:
    for line in text.split("\n"):
        line = line.strip()
        if line:
            return line[:max_chars]
    return ""


def _is_stale(item: RawItem, max_age_hours: int) -> bool:
    if item.published_at is None:
        return True
    pub = item.published_at
    if pub.tzinfo is None:
        pub = pub.replace(tzinfo=timezone.utc)
    age_hours = (datetime.now(timezone.utc) - pub).total_seconds() / 3600
    return age_hours > max_age_hours


class FilterPipeline:
    def __init__(
        self,
        existing_ids: set[str] | None = None,
        existing_titles: list[tuple[str, "datetime | None"]] | None = None,
    ):
        self._dedup = Deduplicator(existing_ids or set(), existing_titles)
        self._scorer = RelevanceScorer()

    def process(self, items: list[RawItem]) -> list[NewsItem]:
        # 1. Recency filter — drop items older than max_age_hours
        fresh = [i for i in items if not _is_stale(i, settings.max_age_hours)]
        stale_count = len(items) - len(fresh)
        if stale_count:
            logger.info(
                f"Recency filter: {stale_count} stale items dropped "
                f"(>{settings.max_age_hours}h old), {len(fresh)} remain"
            )

        # 2. Deduplicate (URL + title similarity)
        unique = self._dedup.filter(fresh)
        dropped_dedup = len(fresh) - len(unique)
        logger.info(f"After dedup: {len(unique)}/{len(fresh)} remain ({dropped_dedup} dropped — URL or title duplicate)")

        accepted: list[NewsItem] = []
        rejected = 0

        for raw in unique:
            score = self._scorer.score(raw)
            if score < settings.min_relevance_score:
                rejected += 1
                continue

            news_item = NewsItem(
                id=str(uuid.uuid4()),
                raw_item_id=raw.id,
                source_name=raw.source_name,
                url=raw.url,
                title=raw.title,
                title_zh=None,
                summary="",
                relevance_score=score,
                tags=[],
                published_at=raw.published_at,
                raw_content=_first_para(raw.content),
            )
            accepted.append(news_item)

        logger.info(
            f"Filter result: {len(accepted)} accepted, {rejected} rejected "
            f"(threshold={settings.min_relevance_score})"
        )
        return accepted
