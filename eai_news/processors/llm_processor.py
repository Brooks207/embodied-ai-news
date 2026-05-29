import json

import anthropic
from loguru import logger

from ..models import NewsCategory, NewsItem

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
4. importance：is_relevant=true 时必填，整数 0-10，评估新闻对具身智能行业从业者的重要程度
   - 9-10：行业里程碑，头部公司重大融资（>5亿）、颠覆性产品首次亮相、大规模量产/商业化落地
   - 7-8：重要事件，知名公司新品发布、重大合作/订单、大额融资、高管关键任命
   - 5-6：常规资讯，中等融资、普通合作、产品迭代更新
   - 3-4：边缘动态，小公司动态、技术论文、活动预告
   - 1-2：几乎无价值，招聘信息、纯转载、无实质内容
   - is_relevant=false 时填 0
5. category：is_relevant=true 时必填，从以下选项中选一个最符合的，填英文 key
   - funding：融资、投资、估值、IPO、并购
   - product：新品发布、产品迭代、Demo、量产、参数发布
   - deployment：落地案例、商业部署、客户订单、工厂/仓储应用
   - talent：人事变动、高管任命、招聘、团队动态
   - supply_chain：供应链、零部件、执行器、芯片、成本
   - policy：政策、监管、补贴、标准制定
   - other：以上均不符合
   - is_relevant=false 时填 other

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
                        "importance": {
                            "type": "integer",
                            "description": "Importance score 0-10 (required if is_relevant=true, else 0)",
                            "minimum": 0,
                            "maximum": 10,
                        },
                        "category": {
                            "type": "string",
                            "description": "News category key (required if is_relevant=true, else 'other')",
                            "enum": ["funding", "product", "deployment", "talent", "supply_chain", "policy", "other"],
                        },
                    },
                    "required": ["id", "is_relevant", "title_zh", "summary", "importance", "category"],
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
                max_tokens=4096,
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
            item.importance = float(u.get("importance", 0))
            raw_cat = u.get("category", "other")
            try:
                item.category = NewsCategory(raw_cat)
            except ValueError:
                item.category = NewsCategory.OTHER
            kept.append(item)

        return kept
