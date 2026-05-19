# EAI 新闻自动化系统 — 技术流程说明

> 文档版本：2026-05-19  
> 项目路径：`/Users/blueye/Desktop/News`

---

## 一、整体流程

```
信息采集（多源）
    ↓
去重
    ↓
相关性粗筛（关键词评分）
    ↓
品类识别（关键词 + LLM 兜底）
    ↓
存储（飞书多维表格 / Excel / SQLite）
```

每隔 2 小时自动触发一次完整流程（由 APScheduler 调度）。

---

## 二、信息来源

信息源配置文件：`eai_news/config/sources.yaml`  
采集器入口：`eai_news/collectors/__init__.py`

系统支持 5 类采集方式，所有采集器并发运行（`asyncio.gather`），单个采集器失败不影响其他源。

### 2.1 RSS 订阅（9 个源）

| 来源 | ID | 重要度 |
|------|----|--------|
| arXiv Robotics | `arxiv_robotics` | ★★★ |
| BAIR Blog（伯克利 AI 研究室）| `bair_blog` | ★★★★★ |
| NVIDIA Developer Blog | `nvidia_dev_blog` | ★★★★ |
| TechCrunch Robotics | `techcrunch_robotics` | ★★★ |
| VentureBeat AI | `venturebeat_ai` | ★★★ |
| Google DeepMind Blog | `deepmind_blog` | ★★★★★ |
| 36氪 机器人 | `36kr_robotics` | ★★★★ |
| 量子位 | `qbitai` | ★★★★ |
| Hugging Face Blog | `hugging_face_blog` | ★★★ |

每个 RSS 源最多抓取最新 30 条条目，解析标题、链接、发布时间、摘要。

### 2.2 Twitter / X 账号（27 个）

分两类监控：

**海外公司官方账号（13 个）**

| 公司 | Handle | 重要度 |
|------|--------|--------|
| Figure AI | `@figure_robot` | ★★★★★ |
| Tesla AI | `@Tesla_AI` | ★★★★★ |
| Physical Intelligence | `@pi_robot_ai` | ★★★★★ |
| Google DeepMind | `@GoogleDeepMind` | ★★★★★ |
| Unitree Robotics | `@UnitreeRobotics` | ★★★★★ |
| 1X Technologies | `@1x_technologies` | ★★★★ |
| Agility Robotics | `@AgilityRobotics` | ★★★★ |
| Apptronik | `@Apptronik_Inc` | ★★★★ |
| Sanctuary AI | `@SanctuaryAIinc` | ★★★★ |
| Covariant | `@covariantai` | ★★★★ |
| Intrinsic | `@intrinsic_ai` | ★★★★ |
| Shadow Robot | `@Shadow_Robot` | ★★★ |
| Dexterity AI | `@DexterityAI` | ★★★ |

**KOL 个人账号（14 个）**

| 姓名 | Handle | 机构 | 重要度 |
|------|--------|------|--------|
| Jim Fan | `@DrJimFan` | NVIDIA | ★★★★★ |
| Sergey Levine | `@svlevine` | UC Berkeley | ★★★★★ |
| Chelsea Finn | `@chelseabfinn` | Stanford | ★★★★★ |
| Pieter Abbeel | `@pabbeel` | Berkeley | ★★★★★ |
| Fei-Fei Li | `@drfeifei` | Spatial Intelligence | ★★★★★ |
| Russ Tedrake | `@russtedrake` | MIT | ★★★★★ |
| Andrej Karpathy | `@karpathy` | 前 Tesla | ★★★★★ |
| Yann LeCun | `@ylecun` | Meta | ★★★★ |
| David Ha | `@hardmaru` | — | ★★★★ |
| Marc Raibert | `@marcraibertbd` | Boston Dynamics | ★★★★ |
| Marco Hutter | `@MarcoHutterETH` | ETH | ★★★★ |
| Ken Goldberg | `@Ken_Goldberg` | Berkeley | ★★★★ |

> **注**：Twitter 采集需配置 `TWITTER_BEARER_TOKEN`，未配置时该渠道自动跳过，不影响其他来源。

### 2.3 YouTube 频道（6 个）

| 频道 | 重要度 |
|------|--------|
| Figure AI | ★★★★★ |
| Boston Dynamics | ★★★★ |
| Agility Robotics | ★★★★ |
| Unitree Robotics | ★★★★★ |
| Google DeepMind | ★★★★★ |
| NVIDIA Robotics | ★★★★ |

> **注**：需配置 `YOUTUBE_API_KEY`，未配置时跳过。部分频道 `channel_id` 待补充。

### 2.4 微博账号（5 个，中国公司）

| 公司 | 微博用户名 | 重要度 |
|------|-----------|--------|
| 宇树科技 | `unitreerobotics` | ★★★★★ |
| 优必选 | `ubtechrobotics` | ★★★★ |
| 傅利叶智能 | `fourier_intelligence` | ★★★★ |
| 智元机器人 | `zhiyuanrobot` | ★★★★★ |
| 银河通用 | `galbot_ai` | ★★★★ |

### 2.5 网站爬虫（11 个，无 RSS 的官网与媒体）

**海外公司官网（6 个）**

| 来源 | URL |
|------|-----|
| Figure AI News | `figure.ai/news` |
| Physical Intelligence Blog | `physicalintelligence.company/blog` |
| 1X Technologies | `1x.tech/discover` |
| Apptronik Press | `apptronik.com/press-release` |
| Sanctuary AI News | `sanctuaryai.com/news` |
| 傅利叶智能 Newsroom | `fftai.com/newsroom` |

**中国公司官网（2 个）**

| 来源 | URL |
|------|-----|
| 宇树科技官网 | `unitree.com/news/` |
| 智元机器人官网 | `zhiyuan-robot.com/news` |

**中文科技媒体（1 个）**

| 来源 | URL |
|------|-----|
| 雷锋网 机器人 | `leiphone.com/category/robot` |

爬虫通过 CSS Selector 提取文章链接，每个链接生成一条 `RawItem`。

---

## 三、相关性粗筛

配置文件：`eai_news/config/filters.yaml`  
实现：`eai_news/filters/relevance_scorer.py`

### 3.1 评分逻辑

每条原始内容（标题 + 正文拼接，统一小写）按以下规则计算相关性得分，满分 10 分：

| 规则 | 分值 |
|------|------|
| 命中**核心关键词**（每个）| +2.0 |
| 命中**支持关键词**（每个）| +0.8 |
| 来源重要度加成（importance 1-5 → 0-2 分）| +0~+2.0 |
| **高价值信源**额外奖励（见下表）| +1.5 ~ +2.0 |
| 命中**排除关键词**（任一）| 直接归零 |

**高价值信源奖励：**

| 信源 ID | 额外加分 |
|---------|---------|
| `tw_jim_fan`、`tw_andrej_karpathy`、`tw_sergey_levine`、`tw_chelsea_finn`、`tw_pieter_abbeel`、`bair_blog`、`deepmind_blog` | +1.5 |
| `tw_figure_robot`、`tw_physical_intelligence`、`tw_unitree`、`web_figure_ai`、`web_physical_intelligence` | +2.0 |

**排除关键词（命中即得 0 分）：**  
`unsubscribe`、`newsletter`、`privacy policy`、`terms of service`、`cookie`

### 3.2 核心关键词（权重 +2.0）

```
具身智能 / embodied ai / embodied intelligence / humanoid robot / humanoid /
人形机器人 / robot learning / foundation model / manipulation / locomotion /
dexterous / 灵巧手 / 双臂 / bimanual / whole body control / 全身控制 /
imitation learning / 模仿学习 / reinforcement learning robotics / robot policy /
legged robot / 足式机器人 / mobile manipulation
```

### 3.3 支持关键词（权重 +0.8）

```
robot / robotics / 机器人 / actuator / 执行器 / sensor / 传感器 /
end effector / 末端执行器 / autonomous / 自主 / teleoperation / 遥操作 /
sim2real / 仿真 / dataset / 数据集
```

### 3.4 筛选阈值

`min_relevance_score = 5.0`（可在 `.env` 中调整）

得分 ≥ 5.0 的条目进入品类识别；低于阈值的直接丢弃。

---

## 四、品类识别（Categorizer）

实现：`eai_news/filters/categorizer.py`

### 4.1 六大品类

| 品类 | Key | 覆盖内容 |
|------|-----|---------|
| 融资 | `funding` | 融资轮次、估值、IPO、并购 |
| 产品 | `product` | 新品发布、迭代、Demo、量产 |
| 落地 | `deployment` | 商业部署、订单、工厂/仓储应用 |
| 人才 | `talent` | 高管任命、人事变动、招聘 |
| 供应链 | `supply_chain` | 零部件、执行器、芯片、成本 |
| 政策 | `policy` | 政策文件、监管、补贴、标准 |
| 其他 | `other` | 以上均不符合 |

### 4.2 识别逻辑（两阶段）

**第一阶段：关键词打分**

对每个品类，统计文本中命中的关键词数量，乘以品类权重（当前均为 1.0），取得分最高的品类。

```
得分 = 命中关键词数 × 权重
```

**第二阶段：LLM 兜底（仅在得分全为 0 时触发）**

当第一阶段所有品类得分均为 0（即关键词完全未命中），调用 Claude Haiku 做一次分类判断：

- 输入：标题 + 正文前 300 字
- 输出：六个品类之一的英文 key，或 `other`
- 模型：`claude-haiku-4-5`（成本约 $0.0001/篇）
- 异常处理：API 失败 → 降级返回 `other`，不影响主流程

此机制解决关键词词库覆盖不足的问题（如公司使用 `unveil`、`debut`、`showcase` 等表达发布新品时，若关键词未命中仍可正确分类）。

### 4.3 部分品类关键词示例

**融资（`funding`）**：融资、投资、funding、raised、series a/b/c/d、million、billion、亿元、估值、valuation、ipo、上市、并购、acquisition……

**产品（`product`）**：发布、launch、release、announced、unveil、debut、showcase、reveal、demo、推出、亮相、量产、next-gen、迭代……

**落地（`deployment`）**：落地、部署、deployed、订单、工厂、factory、warehouse、仓储、物流、医疗、partnership、客户……

**政策（`policy`）**：政策、policy、监管、regulation、标准、standard、补贴、subsidy、工信部、科技部、发改委……

---

## 五、去重机制

实现：`eai_news/filters/deduplicator.py`

基于 URL 的 MD5 哈希值去重（`RawItem.id` 字段）。每次采集前从数据库加载已存在的 ID 集合，采集到的条目若 ID 已存在则直接丢弃。

---

## 六、存储

支持三种后端（可在 `.env` 中通过 `STORAGE_BACKEND` 配置）：

| 后端 | 说明 |
|------|------|
| `feishu`（默认）| 写入飞书多维表格，可实时查看与协作 |
| `excel` | 写入本地 Excel 文件（`eai_news/data/eai_news.xlsx`）|
| `both` | 同时写入飞书与 Excel |
| SQLite | 所有原始条目始终写入本地数据库（用于去重与审计）|

---

## 七、当前局限与后续规划

| 问题 | 现状 | 规划 |
|------|------|------|
| 内容处理（Phase 3）| 中文标题、摘要、标签字段均为空 | LLM 二次筛选 + 信息增强（翻译/摘要/标签）|
| YouTube 频道 ID | 部分待补充 | 手动填入真实 channel_id |
| 微博采集 | 依赖 Cookie，稳定性有限 | 待评估替代方案 |
| 发布自动化（Phase 4）| 未实现 | 对接各平台 API |
| 数据追踪（Phase 6）| 未实现 | 各平台数据回流 |
