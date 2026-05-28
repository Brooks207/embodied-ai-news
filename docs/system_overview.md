# EAI 新闻自动化系统 — 技术流程说明

> 文档版本：2026-05-28 v10
> 项目路径：`/Users/blueye/Desktop/News`
> GitHub：`https://github.com/Brooks207/embodied-ai-news`

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1 | 2026-05-19 | 初始版本 |
| v2 | 2026-05-19 | 删除 arXiv；补充 20+ 新信源；加入信源 tier 体系；去重升级为两阶段；品类关键词扩充；调度从 APScheduler 改为系统 cron |
| v3 | 2026-05-19 | 实现 Stage 3 LLM 处理（title_zh / summary）；加入时效过滤（72h）；采集器熔断机制；批量写入 DB；飞书表格新增摘要字段 |
| v4 | 2026-05-19 | Stage 3 加入假阳性细筛（is_relevant）；修复 LLM 只读标题的 bug，现传入原文首段（≤200字符） |
| v5 | 2026-05-20 | WebCrawler 加入文章正文抓取（trafilatura，前5条）；新增 requirements.txt |
| v6 | 2026-05-20 | 修复 importance 未传入 raw_metadata 的 bug；新增核心关键词 `embodied`、`人形`；source_bonus 首次引入 |
| v7 | 2026-05-21 | RSS 修复（httpx 替代 requests 绕过 SSL）；web_crawler seen_urls bug 修复；新增爬虫 10 个（Agility Robotics、Boston Dynamics、Intrinsic、Dexterity AI、千寻智能 + 5 个学术实验室）；source_bonus 重构为"tier-1 官方站保底 ≥5.5"设计 |
| v8 | 2026-05-28 | 新增 6 个媒体信源（机器之心、Embodied Global、Humanoids Daily、The Robot Report、IEEE Spectrum、TechCrunch Web）|
| v9 | 2026-05-28 | Stage 3 LLM 新增 `importance` 字段（0-10），四字段合并为一次 batch 调用；双轨发文策略（≥7 单独发文，<7 攒 digest）|
| v10 | 2026-05-28 | Playwright 无头浏览器基础设施上线；机器之心（API 响应拦截）、优必选（Playwright + 微信外链）✅ 接入；银河通用（httpx POST API）✅ 接入；RSS 新增 Embodied Global / IEEE Spectrum / CMU RI；Playwright 探测所有 disabled JS 渲染源（Sanctuary AI / Engineered Arts / 星动纪元 / BAAI 均无解）；微信公众号采集评估后确认不可行 |

---

## 一、整体流程

```
信息采集（多源并发）
    ↓
时效过滤（丢弃 >72h 的条目，published_at=None 放行）
    ↓
两阶段去重
    ├─ Stage 1：URL 哈希去重（跨批次，查近 30 天 DB）
    └─ Stage 2：标题模糊去重（批次内，48h 窗口，tier 优先）
    ↓
相关性粗筛（关键词评分 ≥ 5.0）
    ↓
LLM 内容处理（Claude Haiku，批量 15 条/次，Prompt Cache）
    ├─ is_relevant：假阳性细筛，false 直接丢弃
    ├─ title_zh：中文标题（≤30字）
    ├─ summary：2句中文摘要（≤80字）
    ├─ importance：重要性评分（0-10）
    └─ category：品类识别（六大品类）
    ↓
存储（SQLite + 飞书多维表格 / Excel）
```

**调度方式**：APScheduler，默认每 2 小时触发一次完整流程（可在 `.env` 调整 `COLLECT_INTERVAL_HOURS`）。
日志路径：`eai_news/data/logs/eai_news_YYYY-MM-DD.log`

---

## 二、信息来源与 Tier 体系

信息源配置文件：`eai_news/config/sources.yaml`
采集器入口：`eai_news/collectors/__init__.py`
信息源待办文档：`docs/sources_todo.md`

所有采集器并发运行（`asyncio.gather`），单个采集器失败不影响其他源。

### 熔断机制

连续失败 3 次的信源自动跳过本次采集周期，并在日志中记录"circuit open"警告。成功一次后重置计数。

### Tier 定义

| Tier | 类型 | 举例 |
|------|------|------|
| 1 | 官方一手来源（公司官网、官方社媒、KOL 本人） | figure.ai、@figure_robot、@DrJimFan |
| 2 | 垂类专业媒体 / 学术机构 | TechCrunch Robotics、量子位、MIT CSAIL |
| 3 | 综合媒体 | VentureBeat、36氪、雷锋网 |

同一事件被多个信源覆盖时，tier 数字更小的来源优先保留。

---

### 2.1 RSS 订阅（11 个）

| 来源 | Tier | 重要度 |
|------|------|--------|
| BAIR Blog（伯克利 AI 研究室）| 2 | ★★★★★ |
| NVIDIA Developer Blog | 2 | ★★★★ |
| TechCrunch Robotics | 2 | ★★★ |
| VentureBeat AI | 3 | ★★★ |
| Google DeepMind Blog | 1 | ★★★★★ |
| 36氪 机器人 | 3 | ★★★★ |
| 量子位 | 2 | ★★★★ |
| Hugging Face Blog | 3 | ★★★ |
| Embodied Global | 2 | ★★★★ |
| IEEE Spectrum Robotics | 2 | ★★★★ |
| CMU Robotics Institute | 2 | ★★★★ |

每个 RSS 源最多抓取最新 30 条，解析标题、链接、发布时间、摘要。

> arXiv Robotics 已移除（内容过于学术，为原始论文预印本）。

---

### 2.2 Twitter / X 账号（31 个）

需配置 `TWITTER_BEARER_TOKEN`（Basic 套餐 $100/月），未配置时自动跳过。

**海外公司官方账号（16 个，均为 tier 1）**

| 公司 | Handle |
|------|--------|
| Figure AI | `@figure_robot` |
| Tesla AI | `@Tesla_AI` |
| Physical Intelligence | `@pi_robot_ai` |
| Google DeepMind | `@GoogleDeepMind` |
| Unitree Robotics | `@UnitreeRobotics` |
| 1X Technologies | `@1x_technologies` |
| Agility Robotics | `@AgilityRobotics` |
| Apptronik | `@Apptronik_Inc` |
| Sanctuary AI | `@SanctuaryAIinc` |
| Engineered Arts | `@engineeredarts` |
| Skild AI | `@skild_ai` |
| Covariant | `@covariantai` |
| Intrinsic | `@intrinsic_ai` |
| Shadow Robot | `@Shadow_Robot` |
| Dexterity AI | `@DexterityAI` |
| RightHand Robotics | `@RightHandRobot` |

**KOL 个人账号（15 个，均为 tier 1）**

| 姓名 | Handle | 机构 |
|------|--------|------|
| Jim Fan | `@DrJimFan` | NVIDIA |
| Sergey Levine | `@svlevine` | UC Berkeley |
| Chelsea Finn | `@chelseabfinn` | Stanford |
| Pieter Abbeel | `@pabbeel` | Berkeley |
| Fei-Fei Li | `@drfeifei` | Spatial Intelligence |
| Chien-Ming Huang | `@chienminghuang` | Johns Hopkins |
| Russ Tedrake | `@russtedrake` | MIT |
| Yann LeCun | `@ylecun` | Meta |
| David Ha | `@hardmaru` | — |
| Andrej Karpathy | `@karpathy` | 前 Tesla |
| Marc Raibert | `@marcraibertbd` | Boston Dynamics |
| Marco Hutter | `@MarcoHutterETH` | ETH |
| Siddhartha Srinivasa | `@siddhuinfinity` | UW |
| Dieter Fox | `@dieter_fox` | NVIDIA |
| Ken Goldberg | `@Ken_Goldberg` | Berkeley |

---

### 2.3 YouTube 频道（6 个，均为 tier 1）

| 频道 | 重要度 | 备注 |
|------|--------|------|
| Figure AI | ★★★★★ | channel_id 待补充 |
| Boston Dynamics | ★★★★ | ✅ |
| Agility Robotics | ★★★★ | channel_id 待补充 |
| Unitree Robotics | ★★★★★ | channel_id 待补充 |
| Google DeepMind | ★★★★★ | ✅ |
| NVIDIA Robotics | ★★★★ | channel_id 待补充 |

需配置 `YOUTUBE_API_KEY`，未配置时跳过。

---

### 2.4 微博账号（7 个，均为 tier 1）

| 公司 | 微博用户名 | 状态 |
|------|-----------|------|
| 宇树科技 | `unitreerobotics` | ✅ |
| 优必选 | `ubtechrobotics` | ✅ |
| 傅利叶智能 | `fourier_intelligence` | ✅ |
| 智元机器人 | `zhiyuanrobot` | ✅ |
| 银河通用 | `galbot_ai` | ✅ |
| 乐聚机器人 | `乐聚机器人` | 🔍 待验证 |
| 自变量（AGIBOT） | `自变量机器人` | 🔍 待验证 |

---

### 2.5 网站爬虫（共 36 个活跃）

采集器根据 `sources.yaml` 中的标志自动路由到以下三类实现：

| 标志 | 采集器类 | 适用场景 |
|------|---------|---------|
| 无（默认） | `WebCrawler` | httpx 静态抓取，解析 `<a href>` |
| `use_browser: true` | `PlaywrightCrawler` | Chromium 渲染后解析 DOM |
| `collector: jiqizhixin` | `JiqizhixinCollector` | Playwright 拦截 API 响应 |
| `collector: galbot` | `GalbotCollector` | httpx 直调 REST API（无浏览器）|

所有爬虫对前 5 条链接额外抓取文章页，用 `trafilatura` 提取正文首段（≤200字）。

#### Playwright 基础设施

文件：`eai_news/collectors/playwright_crawler.py`

- 全局单例 Chromium 进程（懒加载，进程内共享）
- `asyncio.Semaphore(2)` 限制同时活跃页面数
- 进程退出时调用 `close_browser()` 释放资源
- 当前使用 Playwright 的 active sources：**机器之心**（API 拦截）、**优必选**（DOM 解析 + 微信外链）

**海外公司官网（12 个活跃，2 个已禁用，tier 1）**

| 来源 | URL | 备注 |
|------|-----|------|
| Figure AI | `figure.ai/news` | ✅ |
| Physical Intelligence | `physicalintelligence.company/blog` | ✅ |
| 1X Technologies | `1x.tech/discover` | ✅ |
| Apptronik | `apptronik.com/press-release` | ✅ |
| Skild AI | `skild.ai/blogs` | ✅ |
| RightHand Robotics | `righthandrobotics.com/the-latest` | ✅ |
| SCHUNK | `schunk.com/us/en/latest-news/news` | ✅ |
| Agility Robotics | `agilityrobotics.com/press-releases` | ✅ |
| Dexterity AI | `dexterity.ai/blog` | ✅ |
| Boston Dynamics | `bostondynamics.com/blog` | ✅ |
| Intrinsic | `intrinsic.ai/blog` | ✅ |
| Fourier Intelligence | `fftai.com/newsroom` | ✅ |
| Sanctuary AI | `sanctuaryai.com/news` | ❌ disabled（Cloudflare 拦截，Playwright 同样失效） |
| Engineered Arts | `engineeredarts.co.uk/blog` | ❌ disabled（Playwright 只拿到 1 个 WordPress CDN 链接，RSS 也返回 HTML） |

**中国公司官网（8 个活跃，2 个已禁用，tier 1）**

| 来源 | URL | 采集方式 | 备注 |
|------|-----|---------|------|
| 宇树科技 | `unitree.com/news` | 静态爬虫 | ✅ |
| 智元机器人 | `agibot.com.cn/news` | 静态爬虫 | ✅ |
| 傅利叶智能 | `fftai.com/newsroom` | 静态爬虫 | ✅ |
| 乐聚机器人 | `lejurobot.com/news/latest-news` | 静态爬虫 + allow_external | ✅ 文章链接到微信/CCTV |
| 自变量 AGIBOT | `agibot.com/news` | 静态爬虫 | ✅ |
| 千寻智能 | `spirit-ai.com/news` | 静态爬虫 | ✅ |
| 银河通用 | `galbot.com/news` | `GalbotCollector` | ✅ POST `api.galbot.com/api/v1/web/news/list`，20 条/次，无需浏览器 |
| 优必选 | `ubtrobot.com/cn/news-list` | `PlaywrightCrawler` | ✅ Playwright 渲染 + 微信外链，40 条/次 |
| 星动纪元 | `astribot.com/news` | — | ❌ disabled（Playwright 仅拿到导航链接，无 RSS） |
| 将闲科技 LiberAI | `liberai.cn/news` | — | ❌ disabled（DNS 解析失败） |

**学术实验室（8 个活跃，3 个已禁用，tier 2）**

| 来源 | URL | 备注 |
|------|-----|------|
| MIT CSAIL | `csail.mit.edu/news` | ✅ |
| ETH Zurich RSL | `rsl.ethz.ch/the-lab/news.html` | ✅ |
| 上海人工智能实验室 | `shlab.org.cn/info` | ✅ |
| Stanford Robotics Center | `src.stanford.edu/news` | ✅ |
| Imperial College Robot Intelligence | `imperial.ac.uk/.../robot-intelligence/news/` | ✅ |
| 北京大学智能学院 | `ai.pku.edu.cn/xwgg1/xwxx.htm` | ✅ |
| 清华大学交叉信息研究院 | `iiis.tsinghua.edu.cn/xwdt/yxdt.htm` | ✅ |
| 香港科技大学机器人研究所 | `ri.hkust.edu.hk/news` | ✅ selector `a[href*='ri.hkust.edu.hk/node/']` |
| Toyota Research Institute | `tri.global/news` | ❌ disabled（403 反爬） |
| CMU Robotics Institute | `ri.cmu.edu/news/` | ❌ disabled（Playwright 无文章链接；已改用 RSS） |
| 北京智源研究院 BAAI | `baai.ac.cn/news.html` | ❌ disabled（Playwright 仅导航链接；RSS URL 返回 HTML） |

**媒体（9 个活跃，4 个已禁用，tier 2-3）**

| 来源 | Tier | 采集方式 | 备注 |
|------|------|---------|------|
| 雷锋网 机器人 | 3 | 静态爬虫 | ✅ |
| 机器之心 | 2 | `JiqizhixinCollector` | ✅ Playwright 拦截 `/api/article_library/articles.json`，20 条/次，时间从 slug 提取 |
| Humanoids Daily | 2 | 静态爬虫 | ✅ |
| Embodied Global | 2 | RSS | ✅ 网站 JS 渲染，改用 RSS |
| IEEE Spectrum Robotics | 2 | RSS | ✅ 网站 JS 渲染，改用 RSS |
| TechCrunch Robotics | 2 | RSS | ✅ 分类页 JS 渲染，RSS 已覆盖（`techcrunch_robotics`） |
| The Robot Report | 2 | — | ❌ disabled（403 反爬） |
| Embodied Global Web | 2 | — | ❌ disabled（JS 渲染；RSS 已覆盖） |
| IEEE Spectrum Web | 2 | — | ❌ disabled（JS 渲染；RSS 已覆盖） |
| TechCrunch Category Web | 2 | — | ❌ disabled（JS 渲染；RSS 已覆盖） |

---

## 三、时效过滤

实现：`eai_news/filters/pipeline.py`，配置：`MAX_AGE_HOURS`（默认 72）

| 条件 | 处理 |
|------|------|
| `published_at` 距今 ≤ 72h | 正常进入后续流程 |
| `published_at` 距今 > 72h | 丢弃 |
| `published_at = None` | 放行 |

**72h 的理由：** 覆盖完整周末（周五晚→周一早约 60h），不会把历史存档混入日报。可通过 `.env` 中的 `MAX_AGE_HOURS` 调整。

---

## 四、去重机制

实现：`eai_news/filters/deduplicator.py`

### 两阶段去重

**Stage 1：URL 哈希去重（跨批次）**

`RawItem.id` 为 URL 的 MD5 哈希。每次采集前从数据库加载近 30 天的已有 ID 集合，命中则丢弃，防止同一文章重复入库。

**Stage 2：标题模糊去重（批次内）**

解决同一事件被多个信源覆盖的问题。

1. 按 tier 升序排列（tier 1 在前，一手来源优先）
2. 对每条新内容，检查已接受列表中发布时间差 ≤ 48h 且标题归一化相似度 ≥ 70% 的条目
3. 发现重复则丢弃 tier 更高的那条

---

## 五、相关性粗筛

配置文件：`eai_news/config/filters.yaml`
实现：`eai_news/filters/relevance_scorer.py`

### 评分规则

| 规则 | 分值 |
|------|------|
| 命中**核心关键词**（每个）| +2.0 |
| 命中**支持关键词**（每个）| +0.8 |
| 来源重要度加成（importance 1-5）| +0 ~ +2.0 |
| 高价值信源奖励（source_bonus）| +0.5 ~ +4.5 |
| 命中**排除关键词**（任一）| 直接归零 |

**source_bonus 设计原则**：tier-1 公司官方站和纯机器人实验室均配置"保底自动通过"：`importance_bonus + source_bonus ≥ 5.5`。

| 类型 | importance | source_bonus | 效果 |
|------|-----------|--------------|------|
| tier-1 官网（importance=5） | +2.0 | +3.5 | 自动通过 |
| tier-1 官网（importance=4） | +1.5 | +4.0 | 自动通过 |
| tier-1 官网（importance=3） | +1.0 | +4.5 | 自动通过 |
| 综合学术机构 / 媒体 | — | +1.5～+2.5 | 需关键词过滤 |
| 垂类专精媒体（importance=4）| +1.5 | +3.5 | floor=5.0，接近自动通过 |

主要 source_bonus 映射：

| 信源 | bonus |
|------|-------|
| `web_figure_ai` `web_physical_intelligence` `web_unitree` `web_zhiyuan` | +3.5（importance=5，自动通过） |
| `web_agibot` `web_lejuu` `web_spirit_ai` `web_fourier` `web_1x_tech` `web_apptronik` `web_skild_ai` `web_agility_robotics` `web_boston_dynamics` `web_intrinsic` `web_galbot` `web_ubtech` | +4.0（importance=4，自动通过） |
| `web_engineered_arts` `web_righthand_robotics` `web_schunk` `web_dexterity_ai` | +4.5（importance=3，自动通过） |
| `web_eth_rsl` `cmu_ri_news` | +4.0（纯机器人实验室，自动通过） |
| `embodied_global` `web_humanoids_daily` | +3.5（垂类媒体，floor=5.0） |
| `web_jiqizhixin` `qbitai` `36kr_robotics` `nvidia_dev_blog` | +1.5～+2.0（需关键词过滤） |
| `ieee_spectrum_robotics` `web_robot_report` | +1.5（通用机器人媒体，需关键词过滤） |
| `techcrunch_robotics` | +0.5（综合媒体，严格过滤） |

**筛选阈值：** `MIN_RELEVANCE_SCORE = 5.0`

### 核心关键词（+2.0）

```
具身智能 / embodied ai / embodied intelligence / embodied / humanoid robot / humanoid /
人形机器人 / 人形 / robot learning / foundation model / manipulation / locomotion /
dexterous / 灵巧手 / 双臂 / bimanual / whole body control / 全身控制 /
imitation learning / 模仿学习 / reinforcement learning robotics / robot policy /
legged robot / 足式机器人 / mobile manipulation
```

### 支持关键词（+0.8）

```
robot / robotics / 机器人 / actuator / 执行器 / sensor / 传感器 /
end effector / 末端执行器 / autonomous / 自主 / teleoperation / 遥操作 /
sim2real / 仿真 / dataset / 数据集 / deployment / deploy
```

---

## 六、品类识别

品类识别已合并至 Stage 3 LLM batch call。

### 六大品类

| 品类 | Key | 覆盖内容 |
|------|-----|---------|
| 融资 | `funding` | 融资轮次、估值、IPO、并购 |
| 产品 | `product` | 新品发布、迭代、Demo、量产 |
| 落地 | `deployment` | 商业部署、订单、工厂/仓储应用 |
| 人才 | `talent` | 高管任命、人事变动、招聘 |
| 供应链 | `supply_chain` | 零部件、执行器、芯片、成本 |
| 政策 | `policy` | 政策文件、监管、补贴、标准 |
| 其他 | `other` | 以上均不符合 |

---

## 七、Stage 3：LLM 内容处理

实现：`eai_news/processors/llm_processor.py`
模型：`claude-haiku-4-5-20251001`

| 字段 | 说明 | 约束 |
|------|------|------|
| `is_relevant` | 假阳性细筛 | `false` 直接丢弃 |
| `title_zh` | 中文标题 | ≤30字 |
| `summary` | 2句中文摘要 | ≤80字 |
| `importance` | 重要性评分 | 整数 0-10 |
| `category` | 品类 | 六大品类 enum key |

### importance 评分标准

| 分段 | 分值 | 含义 |
|------|------|------|
| 顶级 | 9-10 | 行业里程碑（头部公司 >5亿融资、颠覆性产品首发） |
| 重要 | 7-8 | **单独发文线**（知名公司新品、重大合作、大额融资） |
| 普通 | 5-6 | 进 digest |
| 次要 | 3-4 | 低优先级 digest |
| 噪声 | 1-2 | 可丢弃（招聘、纯转载） |

### 实现细节

- **批量处理**：15条/次 API 调用
- **Prompt Cache**：系统 Prompt 标记 `cache_control: ephemeral`，同一周期内多批次复用
- **Tool Use**：强制 `tool_choice: any`，保证结构化输出
- **错误隔离**：单批次失败时条目原样保留，下次周期重试
- **降级**：`ANTHROPIC_API_KEY` 未配置时跳过此阶段

### 成本估算

每条目约 200 token 输入，Haiku 价格 $0.25/MTok：每天 12 周期 ≈ **$0.018/天**

---

## 八、存储

### SQLite（本地，始终写入）

路径：`eai_news/data/eai_news.db`
写入方式：`executemany` 批量插入。

### 飞书多维表格

| 飞书字段 | 模型字段 | 类型 |
|---------|---------|------|
| 时间 | `published_at` | 日期 |
| 中文标题 | `title_zh`（无则用原标题）| 文本 |
| 摘要 | `summary` | 文本 |
| 分类 | `category`（中文标签）| 单选 |
| 相关性评分 | `relevance_score` | 数字 |
| 发布者 | `source_name` | 文本 |
| 新闻链接 | `url` | 超链接 |

```bash
python run.py --setup-feishu   # 首次初始化字段
python run.py --process-only   # 对 DB 中 title_zh=None 的条目重新跑 LLM
```

通过 `.env` 中的 `STORAGE_BACKEND` 切换：`feishu`（默认）/ `excel` / `both`

---

## 九、当前局限与后续规划

| 模块 | 现状 | 规划 |
|------|------|------|
| YouTube channel_id | Figure AI / Agility / Unitree / NVIDIA 4 个频道 ID 待补充 | 手动查找填入 |
| 微博采集 | 依赖 Cookie，稳定性有限；部分 UID 待验证 | 待评估替代方案 |
| 微信公众号 | 无公开 API，历史文章列表需登录 Cookie，技术上不可行 | 极佳视界、流形空间、将闲科技等小公司内容通过量子位/机器之心/36氪间接覆盖 |
| JS 渲染无解信源 | Sanctuary AI（Cloudflare）、Engineered Arts（无有效链接）、星动纪元（无文章链接）、BAAI（RSS 和 Playwright 均失效）| 长期观察；等官网改版或 RSS 出现 |
| 平台不支持 | LinkedIn / B站 / 小红书暂无采集器 | 长期规划 |
| importance 阈值调整 | 字段已记录，阈值待实验 | 运行若干周期后根据打分分布确定（暂定 ≥7 单独发文） |
| Stage 3 内容生成（双轨） | 未实现 | importance ≥7：抓全文 → 写独立文章；<7：用标题+首段 → 攒 digest 片段 |
| Stage 4 发布自动化 | 未实现 | 对接微信公众号、小红书等平台 API |
| Stage 6 数据追踪 | 未实现 | 各平台数据回流与运营报表 |
