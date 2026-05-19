from pathlib import Path

import anthropic
import yaml
from loguru import logger

from ..config.settings import settings
from ..models import NewsCategory, RawItem

_FILTERS_PATH = Path(__file__).parent.parent / "config" / "filters.yaml"

_CATEGORY_DESCRIPTIONS = {
    NewsCategory.FUNDING: "融资、投资、估值、IPO、并购",
    NewsCategory.PRODUCT: "新品发布、产品迭代、Demo、量产、参数发布",
    NewsCategory.DEPLOYMENT: "落地案例、商业部署、客户订单、工厂/仓储应用",
    NewsCategory.TALENT: "人事变动、高管任命、招聘、团队动态",
    NewsCategory.SUPPLY_CHAIN: "供应链、零部件、执行器、芯片、成本",
    NewsCategory.POLICY: "政策、监管、补贴、标准制定",
    NewsCategory.OTHER: "以上均不符合",
}

_VALID_VALUES = {c.value for c in NewsCategory}


class Categorizer:
    def __init__(self):
        with open(_FILTERS_PATH) as f:
            cfg = yaml.safe_load(f)
        raw = cfg.get("categories", {})
        self._categories: dict[NewsCategory, tuple[list[str], float]] = {}
        for cat_name, cat_cfg in raw.items():
            try:
                cat = NewsCategory(cat_name)
            except ValueError:
                continue
            keywords = [k.lower() for k in cat_cfg.get("keywords", [])]
            weight = float(cat_cfg.get("weight", 1.0))
            self._categories[cat] = (keywords, weight)

        self._llm: anthropic.Anthropic | None = (
            anthropic.Anthropic(api_key=settings.anthropic_api_key)
            if settings.claude_configured
            else None
        )

    def categorize(self, item: RawItem) -> NewsCategory:
        text = (item.title + " " + item.content).lower()
        scores: dict[NewsCategory, float] = {}
        for cat, (keywords, weight) in self._categories.items():
            hits = sum(1 for kw in keywords if kw in text)
            scores[cat] = hits * weight

        if scores and max(scores.values()) > 0:
            return max(scores, key=lambda c: scores[c])

        return self._llm_categorize(item)

    def _llm_categorize(self, item: RawItem) -> NewsCategory:
        if self._llm is None:
            return NewsCategory.OTHER

        categories_str = "\n".join(
            f"- {cat.value}: {desc}"
            for cat, desc in _CATEGORY_DESCRIPTIONS.items()
            if cat != NewsCategory.OTHER
        )
        prompt = (
            f"你是具身智能行业资讯分类助手。请将以下文章归入最合适的类别，"
            f"只输出类别的英文 key，不要解释。\n\n"
            f"可选类别：\n{categories_str}\n- other: 以上均不符合\n\n"
            f"标题：{item.title}\n"
            f"内容（前300字）：{item.content[:300]}"
        )

        try:
            resp = self._llm.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=16,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text.strip().lower()
            if raw in _VALID_VALUES:
                logger.debug(f"LLM categorized '{item.title[:40]}' → {raw}")
                return NewsCategory(raw)
        except Exception as e:
            logger.warning(f"LLM categorization failed: {e}")

        return NewsCategory.OTHER
