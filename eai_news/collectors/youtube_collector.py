from datetime import datetime, timezone

import httpx

from ..models import RawItem
from .base import BaseCollector

YT_API_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeCollector(BaseCollector):
    """Fetch recent videos from a YouTube channel via Data API v3."""

    def __init__(self, source_id: str, source_name: str, channel_id: str, api_key: str):
        self.source_id = source_id
        self.source_name = source_name
        self.channel_id = channel_id
        self.api_key = api_key

    async def fetch(self) -> list[RawItem]:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                f"{YT_API_BASE}/search",
                params={
                    "key": self.api_key,
                    "channelId": self.channel_id,
                    "part": "snippet",
                    "order": "date",
                    "maxResults": 10,
                    "type": "video",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        items = []
        for item in data.get("items", []):
            video_id = item["id"].get("videoId", "")
            if not video_id:
                continue
            snippet = item.get("snippet", {})
            published_at = None
            try:
                published_at = datetime.fromisoformat(
                    snippet["publishedAt"].replace("Z", "+00:00")
                )
            except Exception:
                pass

            items.append(RawItem(
                source_id=self.source_id,
                source_name=self.source_name,
                url=f"https://www.youtube.com/watch?v={video_id}",
                title=snippet.get("title", ""),
                content=snippet.get("description", ""),
                published_at=published_at,
                raw_metadata={"video_id": video_id, "channel_id": self.channel_id},
            ))
        return items
