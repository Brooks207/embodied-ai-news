from ..models import RawItem


class Deduplicator:
    """Remove items whose URLs already exist in the database."""

    def __init__(self, existing_ids: set[str]):
        self._existing = existing_ids
        self._seen: set[str] = set()

    def is_duplicate(self, item: RawItem) -> bool:
        if item.id in self._existing or item.id in self._seen:
            return True
        self._seen.add(item.id)
        return False

    def filter(self, items: list[RawItem]) -> list[RawItem]:
        return [i for i in items if not self.is_duplicate(i)]
