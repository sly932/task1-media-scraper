# 设计文档 · 媒体内容采集工具

## 1. 选了哪个平台，为什么

**YouTube（Data API v3）。** 四个候选里它是唯一有官方、稳定、字段覆盖完整 API 的平台：`search.list` 拿候选、`videos.list` 拿播放/点赞/发布时间、`channels.list` 拿粉丝数/简介，题目要求的字段全部直接可得。抖音、小红书强反爬且违反 ToS、链路脆弱；TikTok Research API 需审批且门槛高。选 YouTube 把"能不能拿到数据"这个最大风险直接清零，把精力放在筛选/去重/排序的工程质量上。

## 2. 做了哪些调研

- YouTube Data API v3 三个端点的字段与配额成本：`search.list` 约 100 units/次、`videos`/`channels.list` 约 1 unit/次且支持一次 50 个 id 批量，日配额 1 万 → 召回宽度、翻页深度必须设可配上限，且**先 search 拿 id、再批量补详情**，避免逐条调用打满配额。
- 字段缺失情况：部分视频隐藏 `likeCount`，做 0 兜底。
- 健身类内容英文素材显著多于中文 → query 理解阶段强制中英文都扩，提升召回覆盖。

## 3. 整体技术方案与关键决策

| 决策 | 选择 | 理由 |
| --- | --- | --- |
| 抓取方式 | 官方 API 取结构化字段 | 不用 Agent "看"视频，省 token、稳定、字段直接可用 |
| 先规则后 LLM | 硬规则把候选从几十降到十几，再喂模型 | 控 token、控延迟、结果稳定 |
| LLM 只做语义 | query 理解、相关性、去重 | 客观数字不交给 LLM 评判，避免幻觉 |
| 召回主体 | 以视频为主体，回溯频道 | 与"每行同时含账号字段+内容字段"的输出契约一致 |
| 可扩展 | 一个 `PlatformAdapter` 接口 | YouTube 是第一个实现，不做框架级过度抽象 |

**Top 5 的"混合"定义**：召回主体是视频，但去重阶段按创作者折叠——同一账号只保留最相关的一条。所以最终 Top 5 = 5 个不同账号 × 各一条代表作。一行既是一个竞品账号、又是一条可参考内容，一份榜单两用，并天然避免大号刷屏（`config.yaml` 里 `allow_same_account` 可开成允许同号多条）。

## 4. 去重与排序怎么设计的

**去重（两层）**：① LLM 语义去重——给搬运/雷同/同人不同号内容打同一 `dup_group` 标签，这是硬规则做不到、必须靠 LLM 的部分；② 创作者折叠——同 `account_id` 留 `final_score` 最高的一条。先按 dup_group 折叠、再按 creator 折叠。

**排序（语义 + 客观融合）**：
- 语义分：LLM 对每个候选按 rubric 四维（主题契合 / 受众匹配 / 内容形式 / 专业可信）逐维判 Yes/No，命中比例即语义分。**相关性判定和去重打标在同一次 LLM 调用里批量完成，省一半 token。**
- 客观分：`views / likes / followers` 取对数归一（抗长尾），`recency` 按新鲜度归一；各信号权重可配后再归一。客观数字全程不进 LLM。
- `final = 0.6·语义 + 0.4·客观`（权重可配）。

**不足 5 条**：策略可配，默认 `return_fewer`（返回 N<5 并在 stats 标注）；可切 `relax_filters` 放宽硬规则重排。

## 5. 遇到的问题与解决

- **配额易打满** → search 只取 id，详情用 `videos`/`channels.list` 批量（50/次）补全；召回宽度/上限做成配置。
- **token 开销** → 候选批量喂入而非逐条；相关性 + 去重合并为一次调用；只对规则幸存者跑 LLM。
- **LLM 返回不稳定** → `chat_json` 强制 JSON 并带容错解析（剥 ``` 围栏 / 抓首个 JSON 块）。
- **开发期无法联网验证** → 加 `MockAdapter`（本地 fixture）+ `StubLLMClient`（启发式打桩），`LLM_STUB=1 --provider mock` 可在无 key/无网络下端到端跑通逻辑；真实链路一条命令切换。
- **真实 YouTube 数据下 Top5 只剩 1 条**（mock 验不出）→ 定位为 `last_post_within_days` 误杀：adapter 把 `account_last_post_at` 取成了「候选视频自己的发布日期」而非「账号最近一次上传」，而 search 返回任意年龄的相关视频，于是活跃大号的老爆款被当成僵尸号筛掉（40 条全死在这条规则）。**当前修法（配置）**：关闭该过滤 + 召回上限收窄到 20 + 放宽 LLM `timeout/max_tokens`，真实数据稳定出满 Top5。**正确修法（留作 v2）**：adapter 用 `playlistItems.list` 查频道 uploads 的真实最新上传日期填 `account_last_post_at`，让活跃度过滤名副其实。

## 6. 扩展到全部平台会怎么设计

每个平台实现一个 `PlatformAdapter`（`search() → normalize() → 统一 Candidate schema`），pipeline / 规则 / 去重 / 排序 / 输出全部复用、零改动。平台差异（鉴权、反爬、字段映射、配额）封装在各自 Adapter 内。无官方 API 的平台（抖音/小红书）再在 Adapter 内决定走第三方数据源或受控采集，对上层透明。配置、阈值、排序逻辑已与平台解耦。

**故意没做（留作 v2）**：用户反馈影响下次推荐、"在大号下分层召回"、每条结果的深度可借鉴点分析。

## 7. 用到的工具

Python · FastAPI/uvicorn（Web UI）· httpx（HTTP）· PyYAML（配置）· python-dotenv · DeepSeek-V4（SiliconFlow，OpenAI 兼容）· YouTube Data API v3。开发借助 AI coding 工具完成脚手架与迭代。
