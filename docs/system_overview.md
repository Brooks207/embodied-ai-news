# EAI 新闻自动化系统 — 技术流程说明

> 文档版本：2026-05-19 v4
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

### 2.5 网站爬虫（23 个）

爬虫通过 CSS Selector 提取文章链接，每个链接生成一条 `RawItem`。

**海外公司官网（10 个，tier 1）**

| 来源 | URL |
|------|-----|
| Figure AI | `figure.ai/news` |
| Physical Intelligence | `physicalintelligence.company/blog` |
| 1X Technologies | `1x.tech/discover` |
| Apptronik | `apptronik.com/press-release` |
| Sanctuary AI | `sanctuaryai.com/news` |
| Engineered Arts | `engineeredarts.co.uk/blog` |
| Skild AI | `skild.ai/blog` |
| RightHand Robotics | `righthandrobotics.com/news` |
| SCHUNK | `schunk.com/us/en/news` |
| 傅利叶智能 | `fftai.com/newsroom` |

**中国公司官网（6 个，tier 1）**

| 来源 | URL |
|------|-----|
| 宇树科技 | `unitree.com/news` |
| 智元机器人 | `zhiyuan-robot.com/news` |
| 乐聚机器人 | `lejurobot.com/news` |
| 星动纪元 | `astribot.com/news` |
| 自变量 AGIBOT | `agibot.com/news` |
| 将闲科技 LiberAI | `liberai.cn/news` |

**学术实验室（6 个，tier 2）**

| 来源 | URL |
|------|-----|
| MIT CSAIL | `csail.mit.edu/news` |
| Toyota Research Institute | `tri.global/news` |
| CMU Robotics Institute | `ri.cmu.edu/ri-news` |
| ETH Zurich RSL | `rsl.ethz.ch/news-and-events/news` |
| 上海人工智能实验室 | `shlab.org.cn/news` |
| 北京智源研究院 | `baai.ac.cn/news` |

**中文科技媒体（1 个，tier 3）**

| 来源 | URL |
|------|-----|
| 雷锋网 机器人 | `leiphone.com/category/robot` |

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
| 来源重要度加成（importance 1-5）| +0 ~ +2.0 |
| 高价值信源奖励（见下表）| +1.5 ~ +2.0 |
| 命中**排除关键词**（任一）| 直接归零 |

**高价值信源奖励**

| 信源 ID | 额外加分 |
|---------|---------|
| `tw_jim_fan` `tw_andrej_karpathy` `tw_sergey_levine` `tw_chelsea_finn` `tw_pieter_abbeel` `bair_blog` `deepmind_blog` | +1.5 |
| `tw_figure_robot` `tw_physical_intelligence` `tw_unitree` `web_figure_ai` `web_physical_intelligence` | +2.0 |

**排除关键词（命中即得 0 分）：** `unsubscribe` `newsletter` `privacy policy` `terms of service` `cookie`

**筛选阈值：** `MIN_RELEVANCE_SCORE = 5.0`（可在 `.env` 调整）

### 核心关键词（+2.0）

```
具身智能 / embodied ai / embodied intelligence / humanoid robot / humanoid /
人形机器人 / robot learning / foundation model / manipulation / locomotion /
dexterous / 灵巧手 / 双臂 / bimanual / whole body control / 全身控制 /
imitation learning / 模仿学习 / reinforcement learning robotics / robot policy /
legged robot / 足式机器人 / mobile manipulation
```

### 支持关键词（+0.8）

```
robot / robotics / 机器人 / actuator / 执行器 / sensor / 传感器 /
end effector / 末端执行器 / autonomous / 自主 / teleoperation / 遥操作 /
sim2real / 仿真 / dataset / 数据集
```

---

## 六、品类识别

实现：`eai_news/filters/categorizer.py`

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

### 两阶段识别

**Stage 1：关键词打分**

```
得分 = 命中关键词数 × 品类权重（当前均为 1.0）
```

取得分最高的品类。

**Stage 2：LLM 兜底（仅所有品类得分均为 0 时触发）**

调用 `claude-haiku-4-5` 对标题 + 正文前 300 字进行分类，返回品类 key。
成本约 $0.0001/篇，API 失败时降级返回 `other`。

此机制解决词库覆盖不足的问题，如公司使用 `unveil` `debut` `showcase` `reveal` 等高级词汇时仍能正确分类。

---

## 七、Stage 3：LLM 内容处理

实现：`eai_news/processors/llm_processor.py`
模型：`claude-haiku-4-5-20251001`（快速低成本结构化提取）

通过关键词过滤的条目进入 LLM 处理阶段，每条一次调用完成三件事：

| 字段 | 说明 | 约束 |
|------|------|------|
| `is_relevant` | 假阳性细筛 | 关键词误命中（扫地机器人、智能投顾等）直接丢弃 |
| `title_zh` | 中文标题 | ≤30字，信息密度高 |
| `summary` | 2句中文摘要 | ≤80字，聚焦"谁做了什么/融了多少" |

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
- 每周期 30 条 × 2 批 ≈ $0.0015
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
| YouTube channel_id | 4 个频道待补充真实 ID | 手动查找填入 |
| 微博采集 | 依赖 Cookie，稳定性有限 | 待评估替代方案 |
| 待调研信源 | 极佳视界、流形空间、千寻智能、无界动力等 4 家中国公司官网未知 | 人工查找 URL 后加入 |
| 平台不支持 | LinkedIn / B站 / 小红书暂无采集器 | 长期规划 |
| Stage 4 发布自动化 | 未实现 | 对接微信公众号、小红书等平台 API |
| Stage 6 数据追踪 | 未实现 | 各平台数据回流与运营报表 |
