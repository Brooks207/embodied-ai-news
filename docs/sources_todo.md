# 信息源管理文档

> 每次新增/删除信息源后同步更新本文档。
> 最后更新：2026-05-28

---

## 图例

| 状态 | 含义 |
|------|------|
| ✅ 已配置 | 已加入 `sources.yaml`，正常运行 |
| 🔧 待处理 | API/账号未配置，暂时跳过 |
| ⏳ 待添加 | 确认存在但还没加入配置 |
| ❌ 平台不支持 | LinkedIn / B站 / 小红书暂无采集器 |
| 🚫 已禁用 | JS渲染 / 403封锁 / 域名无效，静态爬虫与 Playwright 均无效 |

---

## 海外人形机器人公司

| 公司 | Twitter | 官网爬虫 | YouTube | 备注 |
|------|---------|---------|---------|------|
| Figure AI | 🔧 @figure_robot | ⚠️ figure.ai/news（fetch 超时，偶发） | 🔧 channel_id 待填 | Twitter API 待配置 |
| Tesla AI | 🔧 @Tesla_AI | 🚫 tesla.com（403 全站封锁） | — | Twitter API 待配置 |
| 1X Technologies | 🔧 @1x_technologies | ✅ 1x.tech/discover | — | Twitter API 待配置 |
| Agility Robotics | 🔧 @AgilityRobotics | ✅ agilityrobotics.com/press-releases | 🔧 channel_id 待填 | Twitter API 待配置 |
| Apptronik | 🔧 @Apptronik_Inc | ✅ apptronik.com/press-release | — | Twitter API 待配置 |
| Sanctuary AI | 🔧 @SanctuaryAIinc | 🚫 sanctuaryai.com/news（Cloudflare 拦截，Playwright 也返回 chrome-error） | — | Twitter API 待配置 |
| Engineered Arts | 🔧 @engineeredarts | 🚫 engineeredarts.co.uk/blog（Playwright 只拿到 1 个 WordPress CDN 链接；RSS 返回 HTML） | — | Twitter API 待配置 |
| Boston Dynamics | — | ✅ bostondynamics.com/blog | — | |

---

## Embodied AI 公司

| 公司 | Twitter | 官网爬虫 | 备注 |
|------|---------|---------|------|
| Physical Intelligence | 🔧 @pi_robot_ai | ✅ physicalintelligence.company/blog | Twitter API 待配置 |
| Skild AI | 🔧 @skild_ai | ✅ skild.ai/blogs | Twitter API 待配置 |
| Covariant | 🔧 @covariantai | 🚫 官网 JS 渲染，已被 Amazon 收购，内容停更 | |
| Intrinsic | 🔧 @intrinsic_ai | ✅ intrinsic.ai/blog | Twitter API 待配置 |
| Google DeepMind | 🔧 @GoogleDeepMind | ✅ RSS deepmind.google/blog | 🔧 YouTube API 待配置 |

---

## 灵巧手公司

| 公司 | Twitter | 官网爬虫 | 备注 |
|------|---------|---------|------|
| Shadow Robot | 🔧 @Shadow_Robot | 🚫 shadowrobot.com（文章列表 JS 渲染） | Twitter API 待配置 |
| Dexterity AI | 🔧 @DexterityAI | ✅ dexterity.ai/blog | Twitter API 待配置 |
| RightHand Robotics | 🔧 @RightHandRobot | ✅ righthandrobotics.com/the-latest | Twitter API 待配置 |
| SCHUNK | — | ✅ schunk.com/us/en/latest-news/news | — |

---

## 中国 Embodied AI 公司

| 公司 | 微博 | 官网爬虫 | 备注 |
|------|------|---------|------|
| 宇树科技 | 🔧 unitreerobotics（UID 待验证） | ✅ unitree.com/news | ✅ Twitter |
| 智元机器人 | 🔧 zhiyuanrobot（UID 待验证） | ✅ agibot.com.cn/news | |
| 银河通用 | 🔧 galbot_ai（UID 待验证） | ✅ 专用采集器 `GalbotCollector`，POST `api.galbot.com/api/v1/web/news/list`，20条，无需浏览器 | |
| 优必选 | 🔧 ubtechrobotics（UID 待验证） | ✅ ubtrobot.com/cn/news-list（Playwright + 微信外链，40条） | |
| 傅利叶智能 | 🔧 fourier_intelligence（UID 待验证） | ✅ fftai.com/newsroom | |
| 乐聚机器人 | 🔧 "乐聚机器人"（UID 待验证） | ✅ lejurobot.com/news/latest-news（外链微信） | |
| 星动纪元 | ⏳ 待查 | 🚫 astribot.com/news（Playwright 仅拿到导航链接，无文章；无 RSS） | 微博 handle 未知 |
| 自变量（AGIBOT） | 🔧 "自变量机器人"（UID 待验证） | ✅ agibot.com/news | |
| 将闲科技 LiberAI | ⏳ 待查 | 🚫 域名 DNS 解析失败，无新闻页 | 微博 handle 未知 |
| 极佳视界 | ⏳ 待查 | 🚫 gigaai.cc/blog（博客仅 1 篇，内容主要在微信公众号）| ❌ 微信公众号无公开 API |
| 流形空间 | ⏳ 待查 | 🚫 manifoldai.cn（整站仅 1 条微信外链，内容极少） | ❌ 微信公众号无公开 API |
| 千寻智能 | ⏳ 待查 | ✅ spirit-ai.com/news | |
| 无界动力 | ⏳ 待查 | 🚫 无官网 | |

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
| Google DeepMind | ✅ RSS | — | |
| BAIR（伯克利） | ✅ RSS | — | |
| MIT CSAIL | — | ✅ csail.mit.edu/news | |
| Stanford SRC（Robotics Center） | — | ✅ src.stanford.edu/news | |
| Johns Hopkins LCSR | — | 🚫 lcsr.jhu.edu/news（Cloudflare 拦截） | |
| Toyota Research Institute | — | 🚫 tri.global/news（403 反爬；Playwright 同样 403） | |
| NVIDIA Robotics | ✅ NVIDIA Dev Blog RSS | — | |
| ETH Zurich RSL | — | ✅ rsl.ethz.ch/the-lab/news | |
| CMU Robotics Institute | ✅ RSS（ri.cmu.edu/feed/?post_type=ri-news，100条） | 🚫 web（JS渲染；Playwright 无文章链接）| RSS 2026-05-28 接入 |
| Imperial College Robot Intelligence | — | ✅ imperial.ac.uk/a-z-research/robot-intelligence/news/ | |
| 北京大学智能学院 | — | ✅ ai.pku.edu.cn/xwgg1/xwxx.htm | |
| 清华大学交叉信息研究院 | — | ✅ iiis.tsinghua.edu.cn/xwdt/yxdt.htm | |
| 上海人工智能实验室 | — | ✅ shlab.org.cn/info | |
| 北京智源研究院（BAAI） | — | 🚫 baai.ac.cn/news（Playwright 仅拿到导航链接；RSS URL 返回 HTML）| |
| 香港科技大学机器人研究所 | — | ✅ ri.hkust.edu.hk/news（selector 改为 `a[href*='ri.hkust.edu.hk/node/']`）| |

---

## 专业媒体

| 来源 | 类型 | 状态 | 备注 |
|------|------|------|------|
| 机器之心 | Web（Playwright 响应拦截） | ✅ jiqizhixin.com | 专用采集器 `JiqizhixinCollector`；拦截 `/api/article_library/articles.json`；每次 20 篇；时间从 slug 提取 |
| 量子位 | RSS | ✅ qbitai.com/feed | |
| 36氪 机器人 | RSS | ✅ 36kr.com/feed | |
| 雷锋网 机器人 | Web | ✅ leiphone.com/category/robot | |
| Embodied Global | RSS | ✅ embodiedglobal.com/rss.xml | Web 版 JS 渲染，已禁用 |
| Humanoids Daily | Web | ✅ humanoidsdaily.com | |
| The Robot Report | Web | 🚫 therobotreport.com（403 反爬；Playwright 未尝试，估计同样被拦） | |
| IEEE Spectrum Robotics | RSS | ✅ spectrum.ieee.org/feeds/robotics.rss | Web 版 JS 渲染，已禁用 |
| TechCrunch Robotics | RSS | ✅ techcrunch.com/tag/robotics/feed/（tag RSS）| 分类页 Web 版 JS 渲染，已禁用；RSS 已覆盖 |
| VentureBeat AI | RSS | ✅ venturebeat.com/category/ai/feed/ | |
| Hugging Face Blog | RSS | ✅ huggingface.co/blog/feed.xml | |

---

## 暂不支持的平台

| 平台 | 状态 | 说明 |
|------|------|------|
| Twitter/X | 🔧 | API 402，需升级付费套餐 |
| LinkedIn | ❌ | 无公开 API，反爬严格 |
| B站 | ❌ | 需要账号 Cookie，稳定性差 |
| 小红书 | ❌ | 无公开 API |
| 微博 | 🔧 | Cookie 待配置；UID 解析失败需验证用户名 |

---

## 变更记录

| 日期 | 操作 | 来源 |
|------|------|------|
| 2026-05-19 | 初始化，搭建 RSS / Twitter / YouTube / 微博 / 爬虫 | 建设期 |
| 2026-05-19 | 删除 arXiv（太学术） | 用户反馈 |
| 2026-05-19 | 补充：Engineered Arts、Skild AI、灵巧手、中国公司、学术实验室、KOL | 对齐产品文档 |
| 2026-05-20 | Twitter / YouTube 全部标为🔧待处理（API 未配置，402 错误） | 首次跑通发现 |
| 2026-05-20 | 将闲科技 LiberAI 官网标为🚫（无新闻页，连接失败） | 首次跑通发现 |
| 2026-05-20 | 修正 AGIBOT selector（→ /article/）；乐聚机器人换子页面+外链；星动纪元禁用（JS渲染）| selector 调试 |
| 2026-05-21 | RSS 修复：改用 httpx 取 feed 内容，绕过 SSL 证书问题 | RSS 全部 0 items 根因 |
| 2026-05-21 | 修复 web_crawler seen_urls bug：图标链接先占 URL 导致文字链接被跳过 | SCHUNK/MIT CSAIL 0 items 根因 |
| 2026-05-21 | 修正 Skild AI selector（/blog/ → /blogs/）；修正 RightHand Robotics selector（→ /the-latest/） | selector 调试 |
| 2026-05-21 | 新增：Agility Robotics、Boston Dynamics、Intrinsic | 补充缺失的海外公司 |
| 2026-05-21 | 禁用：Sanctuary AI、Engineered Arts、BAAI、TRI（403）、LiberAI（DNS）、CMU RI（JS渲染） | 排查无效源 |
| 2026-05-21 | source_bonus 重构：tier-1 公司官方站保底 ≥5.5 自动通过；新增多个缺失来源的 bonus | filter 逻辑修正 |
| 2026-05-21 | 新增 Dexterity AI Blog；标注 Tesla AI / Covariant / Shadow Robot / 银河通用 / 优必选 官网无法爬 | 官网调研 |
| 2026-05-21 | 新增学术实验室爬虫：Imperial College、北京大学、清华 IIIS、香港科大；修正 HKUST selector（→ `a[href*='ri.hkust.edu.hk/node/']`）| 学术源扩充 |
| 2026-05-28 | 新增专业媒体：机器之心、Embodied Global、Humanoids Daily、The Robot Report、IEEE Spectrum、TechCrunch | 媒体源扩充 |
| 2026-05-28 | Embodied Global / IEEE Spectrum / TechCrunch Web 版标为🚫（JS渲染），改用 RSS | 测试发现 |
| 2026-05-28 | The Robot Report 标为🚫（403 反爬） | 测试发现 |
| 2026-05-28 | 新增 Playwright 支持：安装 playwright 1.60.0 + Chromium；实现 `PlaywrightCrawler` | 基础设施 |
| 2026-05-28 | 机器之心：实现专用 `JiqizhixinCollector`，Playwright 拦截 `/api/article_library/articles.json`，每次 20 篇 | 调试攻克 |
| 2026-05-28 | 探测所有 disabled JS 渲染源（Playwright + RSS 双路）：Sanctuary AI（Cloudflare）、Engineered Arts（无有效链接）、星动纪元（无文章链接）、BAAI（RSS 返回 HTML）均无解 | Playwright 排查 |
| 2026-05-28 | CMU RI 发现有效 RSS（`ri.cmu.edu/feed/?post_type=ri-news`，100 条），接入 | RSS 发现 |
| 2026-05-28 | 银河通用：发现 POST API `api.galbot.com/api/v1/web/news/list`，实现 `GalbotCollector`（httpx 直调，无 Playwright） | API 发现 |
| 2026-05-28 | 优必选：发现 `/cn/news-list` 页有 65 条微信外链，Playwright + `allow_external` 接入 | Playwright 接入 |
