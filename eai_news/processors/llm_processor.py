import json

import anthropic
from loguru import logger

from ..models import NewsItem

BATCH_SIZE = 15

_SYSTEM_PROMPT = """\
你是具身智能行业的专业编辑。对每条给定的新闻，用 process_news_items 工具返回处理结果：

1. is_relevant：判断是否真正与具身智能/机器人行业相关（true/false）
   - false 的典型情况：robot vacuum（扫地机器人）、robo-advisor（智能投顾）、
     industrial robot arm（传统工业机械臂，非 AI 驱动）、与机器人无关的 AI 新闻
   - 遇到不确定时，倾向 true
2. title_zh：is_relevant=true 时必填，将英文标题翻译为中文（≤30字，信息密度高，去掉冠词）
   - 若标题已是中文，直接保留或精简；is_relevant=false 时可填空字符串
3. summary：is_relevant=true 时必填，用中文写2句摘要（合计≤80字），
   聚焦"谁做了什么 / 发布了什么 / 融了多少"；is_relevant=false 时可填空字符串

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
                        "is_relevant": {
                            "type": "boolean",
                            "description": "True if genuinely related to embodied AI / robotics",
                        },
                        "title_zh": {
                            "type": "string",
                            "description": "Chinese title, ≤30 chars (required if is_relevant=true)",
                        },
                        "summary": {
                            "type": "string",
                            "description": "2-sentence Chinese summary, ≤80 chars (required if is_relevant=true)",
                        },
                    },
                    "required": ["id", "is_relevant", "title_zh", "summary"],
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
            kept = await self._process_batch(batch)
            results.extend(kept)

        filtered = len(items) - len(results)
        logger.info(
            f"LLM stage: {len(results)}/{len(items)} kept"
            + (f", {filtered} false-positive dropped" if filtered else "")
        )
        return results

    async def _process_batch(self, items: list[NewsItem]) -> list[NewsItem]:
        payload = [
            {"id": item.id, "title": item.title, "content": item.raw_content}
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

        kept: list[NewsItem] = []
        for item in items:
            if item.id not in updates:
                logger.debug(f"No LLM result for item {item.id[:8]} ({item.title[:40]})")
                kept.append(item)
                continue
            u = updates[item.id]
            if not u.get("is_relevant", True):
                logger.info(f"False positive dropped: {item.title[:60]}")
                continue
            item.title_zh = u.get("title_zh") or None
            item.summary = u.get("summary", item.summary)
            kept.append(item)

        return kept
