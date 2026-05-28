from datetime import datetime
from enum import Enum
from typing import Optional
import hashlib

from pydantic import BaseModel, Field, model_validator


class NewsCategory(str, Enum):
    FUNDING = "funding"           # 融资
    PRODUCT = "product"           # 产品发布
    DEPLOYMENT = "deployment"     # 落地场景
    TALENT = "talent"             # 人事变动
    SUPPLY_CHAIN = "supply_chain" # 供应链
    POLICY = "policy"             # 政策监管
    OTHER = "other"

CATEGORY_LABELS_ZH = {
    NewsCategory.FUNDING: "融资",
    NewsCategory.PRODUCT: "产品",
    NewsCategory.DEPLOYMENT: "落地",
    NewsCategory.TALENT: "人才",
    NewsCategory.SUPPLY_CHAIN: "供应链",
    NewsCategory.POLICY: "政策",
    NewsCategory.OTHER: "其他",
}


class ItemStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class RawItem(BaseModel):
    id: str = ""
    source_id: str
    source_name: str
    url: str
    title: str
    content: str = ""
    published_at: Optional[datetime] = None
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    raw_metadata: dict = Field(default_factory=dict)
    status: ItemStatus = ItemStatus.PENDING

    @model_validator(mode="after")
    def compute_id(self) -> "RawItem":
        if not self.id:
            self.id = hashlib.md5(self.url.encode()).hexdigest()
        return self


class NewsItem(BaseModel):
    id: str
    raw_item_id: str
    source_name: str
    url: str
    title: str
    title_zh: Optional[str] = None    # 中文标题（Phase 3 由 Claude 补充）
    summary: str = ""
    category: NewsCategory = NewsCategory.OTHER
    relevance_score: float = 0.0
    importance: float = 0.0            # 0-10，LLM 打分；≥7 单独发文，<7 攒 digest
    tags: list[str] = Field(default_factory=list)
    published_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    raw_content: str = ""             # 原文首段摘要，仅内存使用，不持久化
