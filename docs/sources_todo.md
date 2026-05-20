# 信息源管理文档

> 每次新增/删除信息源后同步更新本文档。
> 最后更新：2026-05-20

---

## 图例

| 状态 | 含义 |
|------|------|
| ✅ 已配置 | 已加入 `sources.yaml`，正常运行 |
| 🔍 待验证 | 已加入配置但 handle/URL 需人工确认 |
| ⏳ 待添加 | 确认存在但还没加入配置 |
| 🔧 待处理 | API/账号未配置，暂时跳过 |
| ❌ 平台不支持 | LinkedIn / B站 / 小红书暂无采集器 |
| 🚫 无新闻页 | 官网无新闻/博客板块，无法爬取 |

---

## 海外人形机器人公司

| 公司 | Twitter | 官网爬虫 | YouTube | 备注 |
|------|---------|---------|---------|------|
| Figure AI | 🔧 @figure_robot | ✅ figure.ai/news | 🔧 channel_id 待填 | Twitter API 待配置 |
| Tesla AI | 🔧 @Tesla_AI | — | — | Twitter API 待配置 |
| 1X Technologies | 🔧 @1x_technologies | ✅ 1x.tech/discover | — | Twitter API 待配置 |
| Agility Robotics | 🔧 @AgilityRobotics | — | 🔧 channel_id 待填 | Twitter API 待配置 |
| Apptronik | 🔧 @Apptronik_Inc | ✅ apptronik.com/press-release | — | Twitter API 待配置 |
| Sanctuary AI | 🔧 @SanctuaryAIinc | ✅ sanctuaryai.com/news | — | Twitter API 待配置 |
| Engineered Arts | 🔧 @engineeredarts | ✅ engineeredarts.co.uk/blog | — | Twitter API 待配置 |

---

## Embodied AI 公司

| 公司 | Twitter | 官网爬虫 | 备注 |
|------|---------|---------|------|
| Physical Intelligence | 🔧 @pi_robot_ai | ✅ physicalintelligence.company/blog | Twitter API 待配置 |
| Skild AI | 🔧 @skild_ai | 🔍 skild.ai/blog (404) | Twitter API 待配置；爬虫 URL 需修正 |
| Covariant | 🔧 @covariantai | — | Twitter API 待配置 |
| Intrinsic | 🔧 @intrinsic_ai | — | Twitter API 待配置 |
| Google DeepMind | 🔧 @GoogleDeepMind | ✅ RSS deepmind.google/blog | 🔧 YouTube API 待配置；Twitter API 待配置 |

---

## 灵巧手公司

| 公司 | Twitter | 官网爬虫 | 备注 |
|------|---------|---------|------|
| Shadow Robot | 🔧 @Shadow_Robot | — | Twitter API 待配置 |
| Dexterity AI | 🔧 @DexterityAI | — | Twitter API 待配置 |
| RightHand Robotics | 🔧 @RightHandRobot | 🔍 righthandrobotics.com/news (404) | Twitter API 待配置；爬虫 URL 需修正 |
| SCHUNK | — | 🔍 schunk.com/us/en/news (404) | 爬虫 URL 需修正 |

---

## 中国 Embodied AI 公司

| 公司 | 微博 | 官网爬虫 | 备注 |
|------|------|---------|------|
| 宇树科技 | ✅ unitreerobotics | ✅ unitree.com/news | ✅ Twitter |
| 智元机器人 | ✅ zhiyuanrobot | ✅ zhiyuan-robot.com/news | |
| 银河通用 | ✅ galbot_ai | — | |
| 优必选 | ✅ ubtechrobotics | — | |
| 傅利叶智能 | ✅ fourier_intelligence | ✅ fftai.com/newsroom | |
| 乐聚机器人 | 🔍 "乐聚机器人" | ✅ lejurobot.com/news | 微博 username 待验证 |
| 星动纪元 | ⏳ 待查 | ✅ astribot.com/news | 微博 handle 未知 |
| 自变量（AGIBOT） | 🔍 "自变量机器人" | ✅ agibot.com/news | 微博 username 待验证 |
| 将闲科技 LiberAI | ⏳ 待查 | 🚫 官网无新闻页，连接失败 | 微博 handle 未知 |
| 极佳视界 | ⏳ 待查 | ⏳ 官网 URL 未知 | 需要进一步调研 |
| 流形空间 | ⏳ 待查 | ⏳ 官网 URL 未知 | 需要进一步调研 |
| 千寻智能 | ⏳ 待查 | ⏳ 官网 URL 未知 | 需要进一步调研 |
| 无界动力 | ⏳ 待查 | ⏳ 官网 URL 未知 | 需要进一步调研 |

---

## KOL 个人账号

| 姓名 | Twitter | 备注 |
|------|---------|------|
| Jim Fan | 🔧 @DrJimFan | Twitter API 待配置 |
| Sergey Levine | 🔧 @svlevine | Twitter API 待配置 |
| Chelsea Finn | 🔧 @chelseabfinn | Twitter API 待配置 |
| Pieter Abbeel | 🔧 @pabbeel | Twitter API 待配置 |
| Fei-Fei Li | 🔧 @drfeifei | Twitter API 待配置 |
| Chien-Ming Huang | 🔧 @chienminghuang | Twitter API 待配置；handle 待验证 |
| Russ Tedrake | 🔧 @russtedrake | Twitter API 待配置 |
| Yann LeCun | 🔧 @ylecun | Twitter API 待配置 |
| David Ha | 🔧 @hardmaru | Twitter API 待配置 |
| Andrej Karpathy | 🔧 @karpathy | Twitter API 待配置 |
| Marc Raibert | 🔧 @marcraibertbd | Twitter API 待配置 |
| Marco Hutter | 🔧 @MarcoHutterETH | Twitter API 待配置 |
| Siddhartha Srinivasa | 🔧 @siddhuinfinity | Twitter API 待配置；handle 待验证 |
| Dieter Fox | 🔧 @dieter_fox | Twitter API 待配置；handle 待验证 |
| Ken Goldberg | 🔧 @Ken_Goldberg | Twitter API 待配置 |

---

## 学术实验室

| 实验室 | RSS | 官网爬虫 | 备注 |
|--------|-----|---------|------|
| Google DeepMind | ✅ RSS | 🔧 Twitter API 待配置 | |
| BAIR（伯克利） | ✅ RSS | — | |
| MIT CSAIL | — | ✅ csail.mit.edu/news | |
| Stanford SVL | — | ⏳ 待添加 | |
| Johns Hopkins CIRL | — | ⏳ 待添加 | |
| Toyota Research Institute | — | 🔍 tri.global/news (403) | 反爬，需换策略 |
| NVIDIA Robotics | ✅ NVIDIA Dev Blog | 🔧 Twitter (Jim Fan, Dieter Fox) 待配置 | |
| ETH Zurich RSL | — | 🔍 rsl.ethz.ch/news (404) | URL 需修正 |
| CMU Robotics Institute | — | 🔍 ri.cmu.edu/ri-news (404) | URL 需修正 |
| Imperial College Robot Intelligence | — | ⏳ 待添加 | |
| 北京大学智能学院 | — | ⏳ 待添加 | |
| 清华大学交叉信息研究院 | — | ⏳ 待添加 | |
| 上海人工智能实验室 | — | 🔍 shlab.org.cn/news (404) | URL 需修正 |
| 北京智源研究院（BAAI） | — | ✅ baai.ac.cn/news | |
| 香港科技大学机器人研究所 | — | ⏳ 待添加 | |

---

## 暂不支持的平台

| 平台 | 状态 | 说明 |
|------|------|------|
| LinkedIn | ❌ | 无公开 API，反爬严格 |
| B站 | ❌ | 需要账号 Cookie，稳定性差 |
| 小红书 | ❌ | 无公开 API |

---

## 变更记录

| 日期 | 操作 | 来源 |
|------|------|------|
| 2026-05-19 | 初始化，搭建 RSS / Twitter / YouTube / 微博 / 爬虫 | 建设期 |
| 2026-05-19 | 删除 arXiv（太学术） | 用户反馈 |
| 2026-05-19 | 补充：Engineered Arts、Skild AI、灵巧手、中国公司、学术实验室、KOL | 对齐产品文档 |
| 2026-05-20 | Twitter / YouTube 全部标为🔧待处理（API 未配置，402 错误） | 首次跑通发现 |
| 2026-05-20 | 将闲科技 LiberAI 官网标为🚫（无新闻页，连接失败） | 首次跑通发现 |
| 2026-05-20 | 标注 404 的爬虫源（Skild、RightHand、SCHUNK、CMU、ETH、上海AI实验室） | 首次跑通发现 |
