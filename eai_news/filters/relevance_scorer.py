from pathlib import Path

import yaml

from ..models import RawItem

_FILTERS_PATH = Path(__file__).parent.parent / "config" / "filters.yaml"


class RelevanceScorer:
    def __init__(self):
        with open(_FILTERS_PATH) as f:
            cfg = yaml.safe_load(f)
        self._core_kw: list[str] = [k.lower() for k in cfg.get("core_keywords", [])]
        self._support_kw: list[str] = [k.lower() for k in cfg.get("support_keywords", [])]
        self._exclude_kw: list[str] = [k.lower() for k in cfg.get("exclude_keywords", [])]
        self._source_bonus: dict[str, float] = cfg.get("source_bonus", {})

    def score(self, item: RawItem) -> float:
        text = (item.title + " " + item.content).lower()

        # Hard exclude
        for kw in self._exclude_kw:
            if kw in text:
                return 0.0

        score = 0.0

        for kw in self._core_kw:
            if kw in text:
                score += 2.0

        for kw in self._support_kw:
            if kw in text:
                score += 0.8

        # Source importance bonus (importance 1-5 → up to +2.0)
        importance = item.raw_metadata.get("importance", 3)
        score += (importance - 1) * 0.5

        # Named source bonus
        score += self._source_bonus.get(item.source_id, 0.0)

        return min(10.0, round(score, 2))
