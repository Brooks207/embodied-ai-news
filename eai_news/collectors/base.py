from abc import ABC, abstractmethod
from loguru import logger
from ..models import RawItem


class BaseCollector(ABC):
    source_id: str = ""
    source_name: str = ""

    @abstractmethod
    async def fetch(self) -> list[RawItem]:
        """Fetch raw items from this source. Returns empty list on failure."""
        ...

    async def safe_fetch(self) -> list[RawItem]:
        try:
            items = await self.fetch()
            logger.info(f"[{self.source_name}] fetched {len(items)} items")
            return items
        except Exception as e:
            logger.warning(f"[{self.source_name}] fetch failed: {e}")
            return []
