# EAI 具身智能新媒体全自动化运营平台 — 实现计划

## 需求重述

构建一套端到端 Python 自动化系统，实现具身智能领域资讯的「采集 → 筛选 → 生成 → 发布 → 存储 → 追踪」完整闭环，每日无人工干预地向微信公众号、小红书、微博等平台输出内容。

---

## 系统架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                        调度层 (APScheduler / Cron)           │
└────────────┬──────────────────────────────────┬────────────┘
             ▼                                  ▼
    ┌────────────────┐                 ┌────────────────┐
    │  Stage 1       │                 │  Stage 4       │
    │  信息采集器     │                 │  发布调度器     │
    │  Collector     │                 │  Publisher     │
    └───────┬────────┘                 └───────┬────────┘
            ▼                                  ▲
    ┌────────────────┐                 ┌────────────────┐
    │  Stage 2       │                 │  Stage 3       │
    │  筛选 & 存储   │ ──────────────► │  内容生成器     │
    │  Filter+DB     │                 │  Claude API    │
    └────────────────┘                 └────────────────┘
             │                                  │
             └──────────────┬───────────────────┘
                            ▼
                  ┌────────────────┐
                  │  Stage 5 & 6   │
                  │  存储 & 追踪   │
                  │  SQLite/PG     │
                  └────────────────┘
```

---

## 项目目录结构

```
eai_news/
├── config/
│   ├── settings.py          # 全局配置（API keys、平台账号、调度时间）
│   ├── sources.yaml         # 信息源列表（公司、实验室、KOL）
│   └── filters.yaml         # 筛选规则（关键词、权重）
├── collectors/              # Stage 1
├── filters/                 # Stage 2
├── processors/              # Stage 3
├── publishers/              # Stage 4
├── storage/                 # Stage 5
├── trackers/                # Stage 6
├── scheduler.py             # 主调度入口
├── db/
│   └── schema.sql
├── requirements.txt
└── .env.example
```

---

## 实现阶段

### Phase 0：项目脚手架（基础设施）

**目标**：建立可运行的项目骨架

**步骤**：
- 初始化 Python 项目，`pyproject.toml` + `uv`
- 建立 `.env` 配置体系（所有密钥走环境变量）
- 编写 `sources.yaml`：录入全部 30+ 家公司、15 家实验室、15 位 KOL 的社媒 handle

**复杂度**：Low | 预计 2-3 小时

---

### Phase 1：信息采集层（Collectors）

**目标**：定时从多源抓取原始内容

**子模块**：

| 采集器 | 数据源 | 方式 |
|--------|--------|------|
| `RSSCollector` | 公司官网博客、arXiv | feedparser |
| `TwitterCollector` | X/Twitter KOL & 公司 | Twitter API v2 |
| `YouTubeCollector` | Demo 视频 | YouTube Data API v3 |
| `WeiboCollector` | 中国公司微博 | 微博 API / 爬虫 |
| `LinkedInCollector` | 海外公司 LinkedIn | 爬虫（selenium/playwright） |
| `WebCrawler` | 官网新闻页 | httpx + BeautifulSoup |

**核心接口**：
```python
class BaseCollector:
    async def fetch(self) -> list[RawItem]

@dataclass
class RawItem:
    source_id: str
    url: str
    title: str
    content: str
    published_at: datetime
    raw_metadata: dict
```

**调度频率**：每 2 小时运行一次

**复杂度**：High | 预计 8-12 小时

---

### Phase 2：筛选与存储层（Filter + DB）

**目标**：去重、评分、分类，只保留高质量内容

**数据库 Schema**（SQLite 起步，可迁移 PostgreSQL）：

```sql
-- 原始条目
CREATE TABLE raw_items (
    id TEXT PRIMARY KEY,
    source_id TEXT,
    url TEXT UNIQUE,
    title TEXT,
    content TEXT,
    published_at TIMESTAMP,
    fetched_at TIMESTAMP,
    status TEXT DEFAULT 'pending'  -- pending/accepted/rejected
);

-- 筛选后条目
CREATE TABLE news_items (
    id TEXT PRIMARY KEY,
    raw_item_id TEXT,
    category TEXT,  -- funding/product/deployment/talent/supply_chain/policy
    relevance_score FLOAT,
    summary TEXT,
    tags TEXT,      -- JSON array
    created_at TIMESTAMP
);

-- 发布记录
CREATE TABLE publications (
    id TEXT PRIMARY KEY,
    news_item_ids TEXT,  -- JSON array
    content_type TEXT,   -- daily_brief/weekly_report/video_repost
    platform TEXT,
    content TEXT,
    status TEXT,         -- draft/published/failed
    published_at TIMESTAMP,
    platform_post_id TEXT
);

-- 数据追踪
CREATE TABLE metrics (
    id TEXT PRIMARY KEY,
    publication_id TEXT,
    platform TEXT,
    views INTEGER,
    likes INTEGER,
    shares INTEGER,
    comments INTEGER,
    followers_delta INTEGER,
    recorded_at TIMESTAMP
);
```

**筛选逻辑**：
- URL 去重（hash）
- 关键词过滤（具身智能相关词表）
- LLM 相关性打分（0-10，≥6 入库）
- 自动分类到 6 个选题方向

**复杂度**：Medium | 预计 4-6 小时

---

### Phase 3：内容处理层（Claude API）

**目标**：用 Claude API 将原始新闻生成可发布内容

**三种内容类型**：

```python
class ContentProcessor:
    # 日报短图文（300字内）
    async def generate_daily_brief(self, items: list[NewsItem]) -> DailyBrief

    # 周报长文（1500-3000字）
    async def generate_weekly_report(self, items: list[NewsItem]) -> WeeklyReport

    # 视频 Demo 搬运文案
    async def generate_video_caption(self, item: NewsItem) -> VideoCaption
```

**Prompt 设计要点**：
- 硬信息优先，不加主观评论
- 格式固定（标题 + 要点 + 来源）
- 短图文配信息图描述（供后续图片生成）
- 输出 JSON 结构化，方便各平台适配

**Claude API 用法**：
- 使用 `claude-sonnet-4-6` 生成日报（cost 敏感）
- 使用 `claude-opus-4-7` 生成周报（质量优先）
- 开启 Prompt Caching（system prompt 复用，降低成本）

**复杂度**：Medium | 预计 4-5 小时

---

### Phase 4：发布层（Publishers）

**目标**：将生成内容自动推送至各平台

**各平台方案**：

| 平台 | 方式 | 难度 |
|------|------|------|
| 微信公众号 | 微信公众号 API（草稿箱 + 发布） | Medium |
| 小红书 | 官方创作者 API 或自动化工具 | High |
| 微博 | 微博开放平台 API | Medium |
| 视频号 | 微信视频号 API（视频上传） | High |
| 抖音 | 抖音开放平台 API | Medium |

**发布接口**：
```python
class BasePublisher:
    async def publish(self, content: PublishableContent) -> PublishResult
    async def get_status(self, post_id: str) -> PostStatus
```

**发布调度**：
- 短图文：每日 8:00 发布
- 长文周报：每周五 9:00 发布
- 视频：检测到新 Demo 后 1 小时内发布

**复杂度**：High | 预计 10-15 小时（平台 API 申请是瓶颈）

---

### Phase 5：存储层

（已在 Phase 2 DB 中覆盖）

补充内容：
- 所有发布内容存 `publications` 表
- 每次发布后记录各平台 `post_id`，供追踪使用
- 定期备份 SQLite 文件至本地 / 云存储

**复杂度**：Low | 预计 1-2 小时

---

### Phase 6：数据追踪层（Trackers）

**目标**：定时回拉各平台互动数据，生成运营报告

```python
class BaseTracker:
    async def fetch_metrics(self, post_id: str, platform: str) -> Metrics

async def generate_weekly_operation_report() -> OperationReport:
    # 各平台阅读量、互动率、粉丝增长趋势
    # 内容类型效果对比
    # 热门话题词云
```

**调度**：每日 23:00 回拉当日数据

**复杂度**：Medium | 预计 3-4 小时

---

### Phase 7：调度主程（Orchestrator）

**目标**：整合所有模块，稳定运行

```python
# scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler.add_job(run_collectors,    'interval', hours=2)
scheduler.add_job(run_filter,        'interval', hours=2, minutes=15)
scheduler.add_job(run_daily_publish, 'cron',     hour=8)
scheduler.add_job(run_weekly_report, 'cron',     day_of_week='fri', hour=9)
scheduler.add_job(run_trackers,      'cron',     hour=23)
```

**监控**：失败告警发送至微信 / 邮件 / Telegram

**复杂度**：Low | 预计 2-3 小时

---

## 依赖与外部服务

| 依赖 | 用途 | 备注 |
|------|------|------|
| Claude API | 内容生成 | 需 Anthropic API Key |
| Twitter API v2 | 采集 KOL 推文 | 需开发者账号（$100/月 Basic 起） |
| YouTube Data API | 视频 Demo 检测 | 免费配额有限 |
| 微信公众号 API | 发布 | 需认证服务号 |
| 微博开放平台 API | 发布 | 需企业账号 |
| 抖音开放平台 API | 发布 | 需企业账号 |
| SQLite / PostgreSQL | 存储 | 起步用 SQLite |
| APScheduler | 任务调度 | Python 库 |
| httpx + BeautifulSoup | 网页采集 | Python 库 |
| feedparser | RSS 采集 | Python 库 |

---

## 风险识别

| 风险 | 等级 | 应对方案 |
|------|------|----------|
| 小红书无官方发布 API | **HIGH** | 评估第三方工具（如蒲公英）或暂时手动发布 |
| Twitter API 费用 | **HIGH** | 仅监控高价值 KOL（15人），控制请求频率 |
| 平台反爬封号 | **MEDIUM** | 爬虫加限速、User-Agent 轮换、优先走官方 API |
| LLM 生成内容质量不稳定 | **MEDIUM** | 设置人工审核开关（`requires_review` 字段），初期半自动 |
| 微信公众号 API 发布限制 | **MEDIUM** | 每日限发 1 篇，与内容节奏一致，暂无冲突 |
| 视频版权风险 | **LOW** | 搬运视频注明来源，首发 24 小时内发布 |

---

## 开发顺序

```
Phase 0（脚手架）
    → Phase 2（DB Schema，先有存储再有采集）
    → Phase 1（采集层，从 RSS + Twitter 开始，逐步扩展）
    → Phase 3（内容生成，用已采集数据验证 Claude Prompt）
    → Phase 4（发布层，先打通微信公众号一个平台）
    → Phase 6（追踪层）
    → Phase 7（调度整合）
    → 逐步接入更多平台（微博 → 抖音 → 小红书）
```

---

## 总体复杂度评估

| 维度 | 估计 |
|------|------|
| 核心功能开发 | 35-50 小时 |
| 平台 API 申请与调试 | 5-10 小时（视审核周期） |
| Prompt 调优 | 3-5 小时 |
| 测试与稳定性 | 5-8 小时 |
| **总计** | **约 50-73 小时** |

**整体复杂度：HIGH**（主要瓶颈在平台 API 申请和小红书发布方案）
