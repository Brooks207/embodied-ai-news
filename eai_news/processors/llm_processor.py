import json

import anthropic
from loguru import logger

from ..models import NewsItem

BATCH_SIZE = 15

_SYSTEM_PROMPT = """\
你是具身智能行业的专业编辑。对每条给定的新闻，用 process_news_items 工具返回处理结果：

1. title_zh：将英文标题翻译为中文（≤30字，信息密度高，去掉冠词/无意义限定词）
   - 若标题已是中文，直接保留或精简
2. summary：用中文写2句摘要（合计≤80字），聚焦"谁做了什么 / 发布了什么 / 融了多少"
3. tags：从下列标签中选3-5个（只选最准确的，不要凑数）：
   融资、产品发布、落地场景、人事变动、供应链、政策监管、
   人形机器人、灵巧手、具身AI、强化学习、模仿学习、基础模型、中国、海外

受众是具身智能行业从业者，不需要解释基础概念，术语无需注释。\
"""

_PROCESS_TOOL: dict = {
    "name": "process_news_items",
    "description": "Return processed fields for a batch of news items.",
    "input_schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "title_zh": {
                            "type": "string",
                            "description": "Chinese title, ≤30 chars",
                        },
                        "summary": {
                            "type": "string",
                            "description": "2-sentence Chinese summary, ≤80 chars total",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "3-5 tags from the allowed list",
                        },
                    },
                    "required": ["id", "title_zh", "summary", "tags"],
                },
            }
        },
        "required": ["items"],
    },
}


class LLMProcessor:
    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def process(self, items: list[NewsItem]) -> list[NewsItem]:
        if not items:
            return items

        results: list[NewsItem] = []
        for start in range(0, len(items), BATCH_SIZE):
            batch = items[start : start + BATCH_SIZE]
            processed = await self._process_batch(batch)
            results.extend(processed)

        processed_count = sum(1 for i in results if i.title_zh)
        logger.info(f"LLM processed {processed_count}/{len(results)} items successfully")
        return results

    async def _process_batch(self, items: list[NewsItem]) -> list[NewsItem]:
        payload = [
            {"id": item.id, "title": item.title, "content": item.summary or ""}
            for item in items
        ]
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=2048,
                system=[
                    {
                        "type": "text",
                        "text": _SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                tools=[_PROCESS_TOOL],
                tool_choice={"type": "any"},
                messages=[
                    {
                        "role": "user",
                        "content": json.dumps(payload, ensure_ascii=False),
                    }
                ],
            )
        except anthropic.APIError as e:
            logger.error(f"LLM batch failed (items {[i.id[:8] for i in items]}): {e}")
            return items  # return unchanged; will retry next cycle

        updates: dict[str, dict] = {}
        for block in response.content:
            if block.type == "tool_use" and block.name == "process_news_items":
                for entry in block.input.get("items", []):
                    updates[entry["id"]] = entry
                break

        if not updates:
            logger.warning(f"LLM returned no tool_use for batch of {len(items)}")
            return items

        for item in items:
            if item.id in updates:
                u = updates[item.id]
                item.title_zh = u.get("title_zh") or None
                item.summary = u.get("summary", item.summary)
                item.tags = u.get("tags", item.tags)
            else:
                logger.debug(f"No LLM result for item {item.id[:8]} ({item.title[:40]})")

        return items
