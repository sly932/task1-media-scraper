---
name: media-scraper
description: 引导使用 media-scraper 媒体内容采集工具——帮用户启动（Web UI / CLI / 离线挡位）、跑一条自然语言需求查询、以及在 config.yaml 里调筛选阈值/返回条数/排序权重/rubric 维度。当用户说「启动 media-scraper / 跑一下采集 / 找一批创作者 / 改一下筛选阈值（粉丝/播放/点赞下限）/ 改返回几条 / 调排序权重（语义 vs 热度）/ 改 rubric 维度 / 媒体采集工具怎么用」时触发。
---

# media-scraper 使用引导

**项目根目录（ROOT）**：你 clone 下来的 `task1-media-scraper` 目录。第一次用本 skill 时，先确认 ROOT 的实际绝对路径（问用户或 `find ~ -name run.py -path '*media_scraper*'` 定位），之后所有命令先 `cd "$ROOT"`。

首次需要环境：`python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`，并 `cp .env.example .env` 填好 `SILICONFLOW_API_KEY` / `YOUTUBE_API_KEY`。之后优先用一键脚本 `./start.sh`，不要手动拼一长串命令。

判断用户意图，走下面对应分支。

## A. 启动 / 跑查询

入口统一是 `./start.sh`：

| 用户想要 | 命令 |
|---|---|
| 打开网页界面（运营用，不碰命令行） | `./start.sh`（→ http://127.0.0.1:8000，前台运行，Ctrl+C 退出） |
| 跑一条真实需求 | `./start.sh "用户那句自然语言需求"` |
| 不耗 YouTube 配额（真 LLM+假数据） | `PROVIDER=mock ./start.sh "..."` |
| 全离线自测（不耗任何 key） | `LLM_STUB=1 PROVIDER=mock ./start.sh "..."` |

要点：
- Web UI 是**前台阻塞**进程，后台方式启动再把地址给用户；不要在前台 sleep 等。
- 查询那句话**原样**取用户的需求，别替他改写方向。
- 结果同时打印在终端并写到 `out/results.{json,csv,html}`。
- 连不通时先自检：`source .venv/bin/activate && python -m media_scraper.llm --ping`（应回 `pong`）；key 在 `.env`。
- **坑：shell 若 export 了 `SILICONFLOW_API_KEY`，会覆盖 `.env`**（dotenv 默认不覆盖已存在的环境变量）。命令行通而程序 401/403 时，用 `env -u SILICONFLOW_API_KEY ./start.sh ...` 屏蔽 shell 那把。

## B. 调参数（改 `config.yaml`，不改代码）

`config.yaml` 是所有阈值/开关/权重的唯一来源，改完重跑即可生效。按用户诉求定位：

| 用户说 | 改哪 |
|---|---|
| 粉丝/播放/点赞门槛太松或太严 | `filters.account.min_followers` / `filters.content.min_views` / `min_likes`（各有 `enabled` 开关 + `value` 阈值） |
| 想多/少返回几条 | `ranking.top_k`（默认 5） |
| 召回太多太慢 / LLM 排序超时 | `recall.max_candidates`（默认 20，直接决定 LLM 单次排序规模）；或换更快的模型（`LLM_MODEL`，默认 `DeepSeek-V4-Flash`） |
| 结果不相关 ↔ 不够头部大号 | `ranking.weights`：`semantic`（语义）vs `popularity`（热度），两者和=1 |
| 调相关性判断标准 | `ranking.rubric`（4 条维度，每维 LLM 判 Yes/No，命中比例即语义分） |
| 凑不满 top_k 怎么办 | `shortfall_strategy`：`return_fewer`（返回少于 N）或 `relax_filters`（放宽硬规则重排） |

改完务必**重跑一次验证**（A 节命令），把前后结果差异讲给用户，不要改完就算完。

### 排序权重（weights）的特殊规矩

`ranking.weights` 一旦因用户反馈而调整，**必须同步在 `feedback/rubric-feedback.md` 顶部加一条记录**（日期 / 场景 / 用户反馈 / 系统建议 / 实际修改 `旧值→新值`）。这是该项目约定的反馈调参留痕机制，config 里也有注释指向它。经验法则：抱怨「人不对路」→ 提 `semantic`；抱怨「都是小号」→ 提 `popularity`。

## 已知坑

`filters.account.last_post_within_days` 目前 `enabled: false`——adapter 把该字段取成了「候选视频自己的发布日」而非「账号最近上传」，真实数据下会误杀活跃大号的老视频。别随便打开它；正确修法（查频道 uploads 真实最新上传日）记在 `DESIGN.md` 第 5 节，留作 v2。
