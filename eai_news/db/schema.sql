-- Raw items from collectors (before filtering)
CREATE TABLE IF NOT EXISTS raw_items (
    id          TEXT PRIMARY KEY,
    source_id   TEXT NOT NULL,
    source_name TEXT NOT NULL,
    url         TEXT UNIQUE NOT NULL,
    title       TEXT NOT NULL,
    content     TEXT DEFAULT '',
    published_at TIMESTAMP,
    fetched_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status      TEXT NOT NULL DEFAULT 'pending',
    raw_metadata TEXT DEFAULT '{}'  -- JSON
);

-- Filtered & categorized news items
CREATE TABLE IF NOT EXISTS news_items (
    id              TEXT PRIMARY KEY,
    raw_item_id     TEXT NOT NULL,
    source_name     TEXT NOT NULL,
    url             TEXT NOT NULL,
    title           TEXT NOT NULL,
    title_zh        TEXT,            -- Chinese title (Phase 3)
    summary         TEXT DEFAULT '', -- Chinese summary (Phase 3)
    category        TEXT NOT NULL DEFAULT 'other',
    relevance_score REAL NOT NULL DEFAULT 0,
    importance      REAL NOT NULL DEFAULT 0,
    tags            TEXT DEFAULT '[]',  -- JSON array
    published_at    TIMESTAMP,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (raw_item_id) REFERENCES raw_items(id)
);

-- Published content records (Phase 4+)
CREATE TABLE IF NOT EXISTS publications (
    id              TEXT PRIMARY KEY,
    news_item_ids   TEXT NOT NULL DEFAULT '[]',  -- JSON array
    content_type    TEXT NOT NULL,               -- daily_brief / weekly_report / video_repost
    platform        TEXT NOT NULL,
    content         TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'draft', -- draft / published / failed
    published_at    TIMESTAMP,
    platform_post_id TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Platform metrics for published content (Phase 6)
CREATE TABLE IF NOT EXISTS metrics (
    id               TEXT PRIMARY KEY,
    publication_id   TEXT NOT NULL,
    platform         TEXT NOT NULL,
    views            INTEGER DEFAULT 0,
    likes            INTEGER DEFAULT 0,
    shares           INTEGER DEFAULT 0,
    comments         INTEGER DEFAULT 0,
    followers_delta  INTEGER DEFAULT 0,
    recorded_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (publication_id) REFERENCES publications(id)
);

CREATE INDEX IF NOT EXISTS idx_news_items_created_at ON news_items(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_items_category ON news_items(category);
CREATE INDEX IF NOT EXISTS idx_news_items_score ON news_items(relevance_score DESC);
CREATE INDEX IF NOT EXISTS idx_raw_items_url ON raw_items(url);
CREATE INDEX IF NOT EXISTS idx_publications_platform ON publications(platform, status);
