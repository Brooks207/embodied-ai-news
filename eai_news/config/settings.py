from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Claude
    anthropic_api_key: Optional[str] = None

    # Twitter API v2
    twitter_bearer_token: Optional[str] = None

    # YouTube Data API v3
    youtube_api_key: Optional[str] = None

    # Weibo
    weibo_cookie: Optional[str] = None

    # 飞书 Bitable
    feishu_app_id: Optional[str] = None
    feishu_app_secret: Optional[str] = None
    feishu_bitable_app_token: Optional[str] = None
    feishu_table_id: Optional[str] = None

    # 存储后端
    storage_backend: str = "feishu"   # feishu | excel | both
    db_path: str = "eai_news/data/eai_news.db"
    excel_path: str = "eai_news/data/eai_news.xlsx"

    # 筛选
    min_relevance_score: float = 5.0

    # 调度
    collect_interval_hours: int = 2
    daily_publish_hour: int = 8
    tracker_hour: int = 23

    @property
    def feishu_configured(self) -> bool:
        return all([
            self.feishu_app_id,
            self.feishu_app_secret,
            self.feishu_bitable_app_token,
            self.feishu_table_id,
        ])

    @property
    def twitter_configured(self) -> bool:
        return bool(self.twitter_bearer_token)

    @property
    def youtube_configured(self) -> bool:
        return bool(self.youtube_api_key)

    @property
    def claude_configured(self) -> bool:
        return bool(self.anthropic_api_key)


settings = Settings()
