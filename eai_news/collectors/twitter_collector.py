from datetime import datetime, timezone

import httpx
from loguru import logger

from ..models import RawItem
from .base import BaseCollector

TWITTER_API_BASE = "https://api.twitter.com/2"


class TwitterCollector(BaseCollector):
    """Fetch recent tweets from a Twitter/X user timeline via API v2."""

    def __init__(self, source_id: str, source_name: str, handle: str, bearer_token: str):
        self.source_id = source_id
        self.source_name = source_name
        self.handle = handle
        self.bearer_token = bearer_token
        self._user_id_cache: dict[str, str] = {}

    async def _get_user_id(self, client: httpx.AsyncClient) -> str | None:
        if self.handle in self._user_id_cache:
            return self._user_id_cache[self.handle]
        resp = await client.get(
            f"{TWITTER_API_BASE}/users/by/username/{self.handle}",
            headers={"Authorization": f"Bearer {self.bearer_token}"},
        )
        resp.raise_for_status()
        data = resp.json()
        user_id = data.get("data", {}).get("id")
        if user_id:
            self._user_id_cache[self.handle] = user_id
        return user_id

    async def fetch(self) -> list[RawItem]:
        async with httpx.AsyncClient(timeout=20) as client:
            user_id = await self._get_user_id(client)
            if not user_id:
                logger.warning(f"[Twitter] could not resolve user_id for @{self.handle}")
                return []

            resp = await client.get(
                f"{TWITTER_API_BASE}/users/{user_id}/tweets",
                headers={"Authorization": f"Bearer {self.bearer_token}"},
                params={
                    "max_results": 20,
                    "tweet.fields": "created_at,author_id,entities",
                    "expansions": "attachments.media_keys",
                    "exclude": "retweets,replies",
                },
            )
            resp.raise_for_status()
            tweets = resp.json().get("data", [])

        items = []
        for tweet in tweets:
            tweet_id = tweet["id"]
            url = f"https://twitter.com/{self.handle}/status/{tweet_id}"
            published_at = None
            if "created_at" in tweet:
                try:
                    published_at = datetime.fromisoformat(
                        tweet["created_at"].replace("Z", "+00:00")
                    )
                except Exception:
                    pass

            items.append(RawItem(
                source_id=self.source_id,
                source_name=self.source_name,
                url=url,
                title=tweet["text"][:100],
                content=tweet["text"],
                published_at=published_at,
                raw_metadata={"tweet_id": tweet_id, "handle": self.handle},
            ))
        return items
