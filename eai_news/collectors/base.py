from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from loguru import logger
from ..models import RawItem


@dataclass
class CollectorResult:
    source_id: str
    source_name: str
    items: list[RawItem] = field(default_factory=list)
    ok: bool = True
    error: str = ""


class BaseCollector(ABC):
    source_id: str = ""
    source_name: str = ""

    @abstractmethod
    async def fetch(self) -> list[RawItem]:
        ...

    async def safe_fetch(self) -> CollectorResult:
        try:
            items = await self.fetch()
            logger.info(f"[{self.source_name}] fetched {len(items)} items")
            return CollectorResult(self.source_id, self.source_name, items, ok=True)
        except Exception as e:
            logger.warning(f"[{self.source_name}] fetch failed: {e}")
            return CollectorResult(self.source_id, self.source_name, [], ok=False, error=str(e))
