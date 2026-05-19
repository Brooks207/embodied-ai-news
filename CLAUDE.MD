# EAI 新媒体运营 — 项目总览

## 项目目标

构建一套**全自动化**的具身智能（Embodied AI）垂类资讯平台，覆盖微信公众号、小红书、微博、视频号、抖音等多渠道同步发布。自动化覆盖从信息获取到数据追踪的完整链路，无需人工干预日常运营。

---

## 核心定位

- **受众**：具身智能行业从业者、投资人、产品团队
- **内容基调**：硬信息为主——融资动态、厂商发布、产线落地、政策变化
- **不做**：「什么是具身智能」式科普，默认读者已具备基础认知

---

## 账号名候选

- 具身通典
- 具身百态
- 具身千问 Embodied Daily
- 造体记 Journey to Embodied
- 第五肢 The Fifth Limb

---

## 全自动化流程（6 个 Stage）

```
信息获取 → 信息筛选与存储 → 信息处理 → 信息发布 → 信息与发布渠道存储 → 数据追踪
```

### Stage 1：信息获取
- 定时抓取多源信息（公司官网、社媒账号、学术机构）
- 覆盖中英文双语内容
- 支持 RSS、API、爬虫等多种采集方式

### Stage 2：信息筛选与存储
- 按选题方向（融资/产品/落地/人才/供应链/政策）自动分类
- 去重、相关性打分过滤低质内容
- 持久化存储至数据库，保留原始来源与时间戳

### Stage 3：信息处理
- 自动生成短图文（300 字内 + 配图描述）
- 自动生成每周长文综述（1500-3000 字）
- 视频 Demo 内容识别与搬运标注

### Stage 4：信息发布
- 多平台自动推送（微信公众号、小红书、微博、视频号、抖音）
- 按内容节奏排期：短图文每日 1 篇，长文每周五 1 篇

### Stage 5：信息与发布渠道存储
- 记录每篇内容在各平台的发布状态、链接、发布时间
- 维护渠道账号状态与 API 健康度

### Stage 6：数据追踪
- 追踪各平台阅读量、互动率、粉丝增长
- 定期生成运营报告

---

## 内容节奏

| 类型 | 频率 | 字数 | 平台 |
|------|------|------|------|
| 短图文（每日简讯） | 每日 1 篇，每周 7 篇 | 300 字内 + 信息图 | 小红书、微信公众号、微博、视频号、抖音 |
| 视频 Demo 搬运 | 及时 | — | 视频号、抖音、B站 |
| 长文周报 | 每周五 1 篇 | 1500-3000 字 | 小红书、微信公众号 |

---

## 选题方向（内容筛选标准）

| 方向 | 具体内容 |
|------|----------|
| 融资（资金动向） | 融资轮次、金额、投资方背景、并购整合、IPO 进展 |
| 产品（发布与迭代） | 新机型发布、参数对比、量产时间节点、价格区间 |
| 落地（场景与订单） | 工厂产线、仓储物流、医疗、服务业的部署案例与规模 |
| 人才（关键人事变动） | CXO 变动、核心技术团队流动、高校与产业合作协议 |
| 供应链（上游变化） | 执行器、传感器、芯片价格/供给/新玩家 |
| 政策（监管与标准） | 国内外政策文件、行业标准制定、补贴与准入动态 |

---

## 信息来源

### 公司社媒账号监控列表

**人形机器人**
- Figure AI, Tesla, 1X Technologies, Agility Robotics, Apptronik, Sanctuary AI, Engineered Arts

**Embodied AI**
- Physical Intelligence, Skild AI, Covariant, Intrinsic, Google DeepMind, NVIDIA

**中国 Embodied AI**
- 智元机器人, 宇树科技, 银河通用, 优必选, 傅利叶智能, 乐聚机器人, 星动纪元, 极佳视界, 流形空间, 千寻智能, 无界动力, 将闲科技-LiberAI, 自变量

**灵巧手**
- Shadow Robot, Dexterity, RightHand Robotics, SCHUNK

监控渠道：官网、YouTube、X（Twitter）、LinkedIn、微博、B站、小红书

### 学术实验室

**国际**
- Google DeepMind Robotics
- Stanford Vision and Learning Lab
- Berkeley Artificial Intelligence Research Lab (BAIR)
- MIT Computer Science and Artificial Intelligence Laboratory (CSAIL)
- Johns Hopkins Computational Interaction and Robotics Lab
- Toyota Research Institute
- NVIDIA Robotics Research
- ETH Zurich Robotics Systems Lab
- CMU Robotics Institute
- Imperial College London Robot Intelligence Lab

**国内**
- 北京大学智能学院
- 清华大学交叉信息研究院
- 上海人工智能实验室
- 北京智源研究院
- 香港科技大学机器人研究所

### 个人 KOL 账号

| 姓名 | 领域 |
|------|------|
| Jim Fan | NVIDIA / Embodied AI |
| Sergey Levine | Robot Learning |
| Chelsea Finn | Stanford / Meta-learning |
| Pieter Abbeel | Berkeley / Robot Learning |
| Fei-Fei Li | Spatial Intelligence |
| Chien-Ming Huang | HRI |
| Russ Tedrake | Control |
| Yann LeCun | World Model |
| David Ha | World Model |
| Andrej Karpathy | Tesla Physical AI |
| Marc Raibert | Boston Dynamics |
| Marco Hutter | ETH |
| Siddhartha Srinivasa | 家庭机器人 |
| Dieter Fox | Robot Perception |
| Ken Goldberg | Manipulation |

---

## 技术栈要求（待定）

- **采集层**：定时任务（cron）+ 多源爬虫 / RSS / Social API
- **存储层**：结构化数据库（新闻条目、发布记录、追踪数据）
- **处理层**：LLM（Claude API）负责内容生成与摘要
- **发布层**：各平台 API 或自动化工具
- **追踪层**：各平台数据回流与报表

---

## 开发原则

- 每个 stage 独立模块化，可单独测试与替换
- 所有自动化任务需有失败告警与日志
- 内容生成需保留原始来源引用，不捏造信息
- 优先覆盖中文市场主流平台（微信公众号、小红书）
