import uuid
from loguru import logger

from ..models import RawItem, NewsItem, ItemStatus
from ..config.settings import settings
from .deduplicator import Deduplicator
from .relevance_scorer import RelevanceScorer
from .categorizer import Categorizer


class FilterPipeline:
    def __init__(self, existing_ids: set[str] | None = None):
        self._dedup = Deduplicator(existing_ids or set())
        self._scorer = RelevanceScorer()
        self._categorizer = Categorizer()

    def process(self, items: list[RawItem]) -> list[NewsItem]:
        # 1. Deduplicate
        unique = self._dedup.filter(items)
        logger.info(f"After dedup: {len(unique)}/{len(items)} items remain")

        accepted: list[NewsItem] = []
        rejected = 0

        for raw in unique:
            score = self._scorer.score(raw)
            if score < settings.min_relevance_score:
                rejected += 1
                continue

            category = self._categorizer.categorize(raw)

            news_item = NewsItem(
                id=str(uuid.uuid4()),
                raw_item_id=raw.id,
                source_name=raw.source_name,
                url=raw.url,
                title=raw.title,
                title_zh=None,   # populated in Phase 3
                summary="",      # populated in Phase 3
                category=category,
                relevance_score=score,
                tags=[],
                published_at=raw.published_at,
            )
            accepted.append(news_item)

        logger.info(
            f"Filter result: {len(accepted)} accepted, {rejected} rejected "
            f"(threshold={settings.min_relevance_score})"
        )
        return accepted
