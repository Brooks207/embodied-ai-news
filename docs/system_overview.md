# EAI 新闻自动化系统 — 技术流程说明

> 文档版本：2026-05-28 v9
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
| v6 | 2026-05-20 | 修复 importance 未传入 raw_metadata 的 bug（评分始终按默认值 3 计算）；新增核心关键词 `embodied`、`人形`；支持关键词增加 `deployment`、`deploy`；为 12 个 tier-1 公司官网爬虫配置 source_bonus（1.5～3.0），首次跑通后 33 条新闻入库 |
| v8 | 2026-05-28 | 新增 6 个媒体信源（机器之心、Embodied Global、Humanoids Daily、The Robot Report、IEEE Spectrum Robotics、TechCrunch Robotics Web）；selector 待验证 |
| v9 | 2026-05-28 | Stage 3 LLM 新增 `importance` 字段（0-10 整数），与 is_relevant/title_zh/summary 合并为一次 batch 调用；确立双轨发文策略（importance ≥7 单独发文，<7 攒 digest） |
| v7 | 2026-05-21～25 | RSS 修复（httpx 替代 requests 绕过 SSL）；web_crawler seen_urls bug 修复；新增爬虫：Agility Robotics、Boston Dynamics、Intrinsic、Dexterity AI、千寻智能（共 5 个海外/中国公司）+ Imperial College、Stanford SRC、北大智能学院、清华 IIIS、港科大机器人研究所（共 5 个学术实验室）；禁用：Sanctuary AI、Engineered Arts、BAAI、TRI、CMU RI（JS渲染/403）；source_bonus 重构为"tier-1 官方站保底 ≥5.5 自动通过"设计；修正 Skild AI、RightHand Robotics selector；修正 ETH RSL / SCHUNK / SHLAB URL |

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
品类识别
    ├─ Stage 1：关键词打分
    └─ Stage 2：LLM 兜底（仅得分全为 0 时触发）
    ↓
Stage 3：LLM 内容处理（Claude Haiku，批量 15 条/次，Prompt Cache）
    ├─ title_zh：中文标题（≤30字）
    ├─ summary：2句中文摘要（≤80字）
    └─ tags：3-5 个标签（预设标签列表）
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

每个信源都有 `tier` 标签，用于去重时的优先级判断：

| Tier | 类型 | 举例 |
|------|------|------|
| 1 | 官方一手来源（公司官网、官方社媒、KOL 本人） | figure.ai、@figure_robot、@DrJimFan |
| 2 | 垂类专业媒体 / 学术机构 | TechCrunch Robotics、量子位、MIT CSAIL |
| 3 | 综合媒体 | VentureBeat、36氪、雷锋网 |

同一事件被多个信源覆盖时，tier 数字更小的来源优先保留。

---

### 2.1 RSS 订阅（8 个）

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

### 2.5 网站爬虫（32 个活跃，7 个已禁用）

爬虫访问列表页，提取文章链接；对前 5 条链接额外抓取文章页，用 `trafilatura` 提取正文首段（≤200字符）写入 `RawItem.content`。第 6 条起仅保留链接和标题，`content` 为空。并发抓取上限 3 个，单篇失败不影响其他条目。

**海外公司官网（11 个活跃，2 个已禁用，tier 1）**

| 来源 | URL | 备注 |
|------|-----|------|
| Figure AI | `figure.ai/news` | ✅ |
| Physical Intelligence | `physicalintelligence.company/blog` | ✅ |
| 1X Technologies | `1x.tech/discover` | ✅ |
| Apptronik | `apptronik.com/press-release` | ✅ |
| Skild AI | `skild.ai/blogs` | ✅ selector 已修正（/blogs/） |
| RightHand Robotics | `righthandrobotics.com/the-latest` | ✅ selector 已修正 |
| SCHUNK | `schunk.com/us/en/latest-news/news` | ✅ |
| Agility Robotics | `agilityrobotics.com/press-releases` | ✅ 新增 |
| Dexterity AI | `dexterity.ai/blog` | ✅ 新增 |
| Boston Dynamics | `bostondynamics.com/blog` | ✅ 新增 |
| Intrinsic | `intrinsic.ai/blog` | ✅ 新增 |
| Sanctuary AI | `sanctuaryai.com/news` | ❌ disabled（JS 渲染） |
| Engineered Arts | `engineeredarts.co.uk/blog` | ❌ disabled（JS 渲染） |

**中国公司官网（6 个活跃，2 个已禁用，tier 1）**

| 来源 | URL | 备注 |
|------|-----|------|
| 宇树科技 | `unitree.com/news` | ✅ |
| 智元机器人 | `agibot.com.cn/news` | ✅ |
| 傅利叶智能 | `fftai.com/newsroom` | ✅ |
| 乐聚机器人 | `lejurobot.com/news/latest-news` | ✅ allow_external（文章链接到微信/CCTV）|
| 自变量 AGIBOT | `agibot.com/news` | ✅ 标题截断，见 source_bonus 说明 |
| 千寻智能 | `spirit-ai.com/news` | ✅ 新增 |
| 星动纪元 | `astribot.com/news` | ❌ disabled（JS 渲染） |
| 将闲科技 LiberAI | `liberai.cn/news` | ❌ disabled（DNS 解析失败） |

**学术实验室（8 个活跃，3 个已禁用，tier 2）**

| 来源 | URL | 备注 |
|------|-----|------|
| MIT CSAIL | `csail.mit.edu/news` | ✅ |
| ETH Zurich RSL | `rsl.ethz.ch/the-lab/news.html` | ✅ |
| 上海人工智能实验室 | `shlab.org.cn/info` | ✅ |
| Stanford Robotics Center | `src.stanford.edu/news` | ✅ 新增 |
| Imperial College Robot Intelligence | `imperial.ac.uk/.../robot-intelligence/news/` | ✅ 新增 |
| 北京大学智能学院 | `ai.pku.edu.cn/xwgg1/xwxx.htm` | ✅ 新增 |
| 清华大学交叉信息研究院 | `iiis.tsinghua.edu.cn/xwdt/yxdt.htm` | ✅ 新增 |
| 香港科技大学机器人研究所 | `ri.hkust.edu.hk/news` | ✅ 新增 |
| Toyota Research Institute | `tri.global/news` | ❌ disabled（403 反爬） |
| CMU Robotics Institute | `ri.cmu.edu/news/` | ❌ disabled（文章列表 JS 渲染） |
| 北京智源研究院 | `baai.ac.cn/news.html` | ❌ disabled（JS 渲染） |

**中文科技媒体（2 个，tier 2-3）**

| 来源 | Tier | URL | 备注 |
|------|------|-----|------|
| 雷锋网 机器人 | 3 | `leiphone.com/category/robot` | ✅ |
| 机器之心 | 2 | `jiqizhixin.com` | ⏳ 首页文章；文章库付费不抓 |

**专业媒体（海外，5 个，tier 2）**

| 来源 | URL | 备注 |
|------|-----|------|
| Embodied Global | `embodiedglobal.com` | ⏳ selector 待验证 |
| Humanoids Daily | `humanoidsdaily.com` | ⏳ selector 待验证 |
| The Robot Report | `therobotreport.com` | ⏳ selector 待验证 |
| IEEE Spectrum Robotics | `spectrum.ieee.org/topic/robotics` | ⏳ selector 待验证 |
| TechCrunch Robotics (Web) | `techcrunch.com/category/robotics` | ⏳ RSS tag/robotics 已有；category 互补 |

> ⏳ = 已加入 `sources.yaml`，selector 正确性待 `python test_sources.py --web-only` 验证。

---

## 三、时效过滤

实现：`eai_news/filters/pipeline.py`，配置：`MAX_AGE_HOURS`（默认 72）

在进入去重和相关性评分之前，先按发布时间过滤：

| 条件 | 处理 |
|------|------|
| `published_at` 距今 ≤ 72h | 正常进入后续流程 |
| `published_at` 距今 > 72h | 丢弃（爬虫抓到历史文章的情况） |
| `published_at = None` | 放行（部分网站无法解析发布时间） |

**72h 的理由：** 覆盖完整周末（周五晚→周一早约 60h），仍属当期新闻，不会把历史存档混入日报。可通过 `.env` 中的 `MAX_AGE_HOURS` 调整。

---

## 四、去重机制

实现：`eai_news/filters/deduplicator.py`

### 两阶段去重

**Stage 1：URL 哈希去重（跨批次）**

`RawItem.id` 为 URL 的 MD5 哈希。每次采集前从数据库加载近 30 天的已有 ID 集合，命中则丢弃，防止同一文章重复入库。

**Stage 2：标题模糊去重（批次内）**

解决同一事件被多个信源覆盖的问题（如官网发布 → 媒体跟进报道）。

1. 将当次批次内所有条目**按 tier 升序排列**（tier 1 在前，保证一手来源优先）
2. 对每条新内容，检查已接受列表中是否存在满足以下两个条件的条目：
   - 发布时间差 ≤ 48 小时
   - 标题归一化后相似度 ≥ 70%（`difflib.SequenceMatcher`）
3. 若发现重复，丢弃当前条目（tier 更高的那条）

**效果示例：**
- Figure AI 官网发布新品（tier 1）→ TechCrunch 同日报道（tier 2）→ 保留官网，丢弃 TechCrunch
- 宇树科技微博发布（tier 1）→ 量子位次日转载（tier 2）→ 保留微博原文

---

## 五、相关性粗筛

配置文件：`eai_news/config/filters.yaml`
实现：`eai_news/filters/relevance_scorer.py`

### 评分规则

| 规则 | 分值 |
|------|------|
| 命中**核心关键词**（每个）| +2.0 |
| 命中**支持关键词**（每个）| +0.8 |
| 来源重要度加成（importance 1-5，由采集器注入 raw_metadata）| +0 ~ +2.0 |
| 高价值信源奖励（见下表）| +1.0 ~ +3.0 |
| 命中**排除关键词**（任一）| 直接归零 |

**高价值信源奖励（source_bonus 设计原则）**

v7 重构后，tier-1 公司官方站和纯机器人实验室均配置"保底自动通过"：`importance_bonus + source_bonus ≥ 5.5`，无需关键词命中即可入库。综合学术机构和媒体信源仍需关键词过滤，仅加小 bonus 降低误杀率。

| 类型 | importance | source_bonus | 总分下限 | 效果 |
|------|-----------|--------------|---------|------|
| tier-1 官网（importance=5） | +2.0 | +3.5 | 5.5 | 自动通过 |
| tier-1 官网（importance=4） | +1.5 | +4.0 | 5.5 | 自动通过 |
| tier-1 官网（importance=3） | +1.0 | +4.5 | 5.5 | 自动通过 |
| 纯机器人实验室官网（importance=4） | +1.5 | +4.0 | 5.5 | 自动通过 |
| KOL Twitter | — | +1.5 | — | 需关键词过滤 |
| 顶级公司 Twitter | — | +2.0 | — | 需关键词过滤 |
| 综合学术机构 / 媒体 | — | +1.5～+2.5 | — | 需关键词过滤 |

具体 ID 映射（`filters.yaml` → `source_bonus`）：

| 信源 | bonus | 备注 |
|------|-------|------|
| `web_figure_ai` `web_physical_intelligence` `web_unitree` `web_zhiyuan` | +3.5 | importance=5，自动通过 |
| `web_agibot` `web_lejuu` `web_spirit_ai` `web_fourier` `web_1x_tech` `web_apptronik` `web_skild_ai` `web_agility_robotics` `web_boston_dynamics` `web_intrinsic` `web_sanctuary_ai` | +4.0 | importance=4，自动通过 |
| `web_engineered_arts` `web_righthand_robotics` `web_schunk` `web_dexterity_ai` | +4.5 | importance=3，自动通过 |
| `web_eth_rsl` `web_tri` `web_cmu_ri` | +4.0 | 纯机器人实验室，自动通过 |
| `tw_jim_fan` `tw_andrej_karpathy` `tw_sergey_levine` 等 KOL | +1.5 | 内容不一定全是机器人，保留关键词过滤 |
| `tw_figure_robot` `tw_physical_intelligence` `tw_unitree` | +2.0 | 顶级公司 Twitter，需关键词过滤 |
| `bair_blog` `deepmind_blog` | +2.0 | 综合学术 RSS，需关键词过滤 |
| `web_shlab` | +2.5 | 综合学术爬虫 |
| `web_baai` `web_mit_csail` | +2.0 | 综合学术爬虫 |
| `qbitai` `36kr_robotics` `nvidia_dev_blog` `web_leiphone_robot` | +1.5 | 垂类媒体，需关键词过滤 |
| `techcrunch_robotics` | +0.5 | 综合媒体，严格关键词过滤 |
| `web_embodied_global` `web_humanoids_daily` | +3.5 | 垂类专精媒体（importance=4），floor=5.0，接近自动通过 |
| `web_jiqizhixin` | +2.0 | 中文AI媒体，需关键词过滤 |
| `web_robot_report` `web_ieee_spectrum` | +1.5 | 通用机器人行业媒体，需关键词过滤 |
| `web_techcrunch_cat` | +0.5 | TechCrunch 类目页爬虫，与 RSS 互补 |

> **AGIBOT 特殊说明**：`agibot.com` 列表页对标题做了服务端截断（如"Hum…"代替"Humanoid"），文章页为 JS 渲染且有 Premium 付费墙，爬虫只能拿到不完整标题。`source_bonus +4.0`（importance=4）确保即使标题残缺也能保底通过，同时零关键词的导航条目（如"Previous123456Next"）因 importance_bonus+source_bonus=5.5 仍被过滤（当无关键词时总分=0+5.5=5.5，恰好通过；纯导航页无内容，LLM 假阳性细筛会将其丢弃）。

**排除关键词（命中即得 0 分）：** `unsubscribe` `newsletter` `privacy policy` `terms of service` `cookie`

**筛选阈值：** `MIN_RELEVANCE_SCORE = 5.0`（可在 `.env` 调整）

### 核心关键词（+2.0）

```
具身智能 / embodied ai / embodied intelligence / embodied / humanoid robot / humanoid /
人形机器人 / 人形 / robot learning / foundation model / manipulation / locomotion /
dexterous / 灵巧手 / 双臂 / bimanual / whole body control / 全身控制 /
imitation learning / 模仿学习 / reinforcement learning robotics / robot policy /
legged robot / 足式机器人 / mobile manipulation
```

> `embodied` 和 `人形` 独立成词后加入（v6），分别解决英文标题被网站截断（"Embodied…"）和中文标题含"人形轮臂"等未含完整"人形机器人"的情况。

### 支持关键词（+0.8）

```
robot / robotics / 机器人 / actuator / 执行器 / sensor / 传感器 /
end effector / 末端执行器 / autonomous / 自主 / teleoperation / 遥操作 /
sim2real / 仿真 / dataset / 数据集 / deployment / deploy
```

---

## 六、品类识别

品类识别已合并至 Stage 3 LLM batch call，不再有独立实现文件。

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

LLM 在同一 batch call 中输出 `category` 字段（enum，见上表 key），FilterPipeline 阶段默认填 `other`，LLM 处理后覆盖写入。

---

## 七、Stage 3：LLM 内容处理

实现：`eai_news/processors/llm_processor.py`
模型：`claude-haiku-4-5-20251001`（快速低成本结构化提取）

通过关键词过滤的条目进入 LLM 处理阶段，每条一次调用完成四件事：

| 字段 | 说明 | 约束 |
|------|------|------|
| `is_relevant` | 假阳性细筛 | 关键词误命中（扫地机器人、智能投顾等）直接丢弃 |
| `title_zh` | 中文标题 | ≤30字，信息密度高 |
| `summary` | 2句中文摘要 | ≤80字，聚焦"谁做了什么/融了多少" |
| `importance` | 重要性评分 | 整数 0-10，见下方评分标准 |
| `category` | 品类 | 六大品类 enum key，见第六节 |

### importance 评分标准

| 分段 | 分值 | 含义 | 例子 |
|------|------|------|------|
| 顶级 | 9-10 | 行业里程碑 | 头部公司 >5亿融资、颠覆性产品首发、大规模量产落地 |
| 重要 | 7-8 | **单独发文线** | 知名公司新品发布、重大合作/订单、大额融资、高管关键任命 |
| 普通 | 5-6 | 进 digest | 中等融资、普通合作、产品迭代更新 |
| 次要 | 3-4 | 低优先级 digest | 小公司动态、技术论文、活动预告 |
| 噪声 | 1-2 | 可丢弃 | 招聘信息、纯转载、无实质内容 |

`importance` 字段存储于 `NewsItem.importance`，当前阶段仅记录，阈值调整见"后续规划"。

### LLM 输入

每条发送：
- `title`：完整标题
- `content`：原文首段，最多 200 字符（从 `RawItem.content` 截取；内容为空时传空字符串）

### 假阳性细筛

关键词粗筛存在误命中（如 robot vacuum、robo-advisor、传统工业机械臂）。LLM 读完首段后判断 `is_relevant`，`false` 的条目在保存前直接丢弃，日志记录 `False positive dropped`。不确定时倾向 `true`，避免漏掉边缘案例。

### 实现细节

- **批量处理**：15条/次 API 调用
- **Prompt Cache**：系统 Prompt 标记 `cache_control: ephemeral`，同一周期内多批次复用缓存
- **Tool Use**：强制 `tool_choice: any`，保证结构化输出
- **错误隔离**：单批次 API 失败时条目原样保留，下次周期重试
- **降级**：`ANTHROPIC_API_KEY` 未配置时跳过此阶段

### 成本估算

每条目约 200 token 输入，Haiku 价格 $0.25/MTok：
- 每周期 30 条 × 2 批 ≈ $0.0015（importance 合并后无额外成本）
- 每天 12 周期 ≈ **$0.018/天**

### 补跑命令

```bash
python run.py --process-only   # 对 DB 中 title_zh=None 的条目重新跑 LLM
```

---

## 八、存储

### SQLite（本地，始终写入）

路径：`eai_news/data/eai_news.db`
所有 raw_items 和 news_items 均写入，用于去重、审计和补跑。
写入方式：`executemany` 批量插入（每周期一次连接）。

### 飞书多维表格

写入字段：

| 飞书字段 | 模型字段 | 类型 |
|---------|---------|------|
| 时间 | `published_at` | 日期 |
| 中文标题 | `title_zh`（无则用原标题）| 文本 |
| 摘要 | `summary` | 文本 |
| 分类 | `category`（中文标签）| 单选 |
| 相关性评分 | `relevance_score` | 数字 |
| 发布者 | `source_name` | 文本 |
| 新闻链接 | `url` | 超链接 |

首次初始化字段：
```bash
python run.py --setup-feishu
```

### 存储后端切换

通过 `.env` 中的 `STORAGE_BACKEND` 切换：`feishu`（默认）/ `excel` / `both`

---

## 九、当前局限与后续规划

| 模块 | 现状 | 规划 |
|------|------|------|
| YouTube channel_id | Figure AI / Agility Robotics / Unitree / NVIDIA 4 个频道待补充真实 ID | 手动查找填入 |
| 微博采集 | 依赖 Cookie，稳定性有限；7 个账号 UID 待验证 | 待评估替代方案 |
| 待调研信源 | 极佳视界（微信公众号为主）、流形空间（内容极少）、无界动力（无官网）共 3 家无法采集 | 长期观察 |
| JS 渲染信源 | Sanctuary AI、Engineered Arts、星动纪元、BAAI、CMU RI 等已禁用，内容暂时缺失 | 考虑 Playwright / 付费代理方案 |
| 平台不支持 | LinkedIn / B站 / 小红书暂无采集器 | 长期规划 |
| importance 阈值调整 | 字段已记录（0-10），阈值待实验 | 运行若干周期后根据打分分布确定最终阈值（暂定 ≥7 单独发文） |
| Stage 3 内容生成（双轨） | 未实现 | importance ≥7：抓全文 → 写独立文章；<7：用已有标题+首段 → 攒 digest 片段 |
| Stage 4 发布自动化 | 未实现 | 对接微信公众号、小红书等平台 API |
| Stage 6 数据追踪 | 未实现 | 各平台数据回流与运营报表 |
