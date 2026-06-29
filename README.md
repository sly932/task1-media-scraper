# 媒体内容采集工具（YouTube 首发）

面向内容运营团队：输入一段健身内容方向的自然语言需求，自动从平台**发现 → 规则筛选 → LLM 去重排序**，给出最相关的 **Top 5**，用于竞品分析与选题参考。

```
自然语言 query
  │ ① query 理解（LLM 扩中英文关键词）
  ▼ ② 宽召回（平台 API，取并集，控配额）
候选集
  │ ③ 规则筛选（可配置，先做，砍掉大部分）
  ▼ ④ LLM 去重折叠 + 语义相关性
  │ ⑤ 融合排序（语义 + 客观热度）
  ▼
Top 5 ──► JSON / CSV / HTML + Web UI
```

## ✨ 亮点

- **一句中文就能用**：运营不用懂关键词/API，自然语言描述方向即可。LLM 自动扩成**中英文混合关键词**并集召回，中英文创作者一网打尽（Top5 实测中英混排）。
- **先规则后 LLM，省钱省 token**：便宜的硬规则先把候选砍掉大半，只对幸存者调一次 LLM——且**相关性判定 + 语义去重合并成同一次调用**，省一半开销。客观数字（播放/点赞/粉丝/新鲜度）本地对数归一，不喂模型。
- **语义 × 热度融合排序**：rubric 逐维命中比例算语义分，客观信号算热度分，`final = 语义·w + 热度·w` 加权融合，权重可调。
- **两级智能去重折叠**：先按语义 `dup_group` 折掉搬运/雷同，再按创作者折叠——Top5 = **5 个不同账号**的混合榜，一行同时是竞品账号 + 参考内容。
- **全部可配，零改代码**：`config.yaml` 调筛选阈值、召回宽度、排序权重、rubric 维度、返回条数、不足策略。
- **反馈调参留痕**：排序权重每次因反馈调整都按时间记进 [`feedback/rubric-feedback.md`](./feedback/rubric-feedback.md)（场景→反馈→建议→改动），可追溯、可回滚。
- **平台可扩展**：`PlatformAdapter` 接口，接新平台（抖音/小红书…）只写一个 adapter，pipeline/规则/排序/输出全复用、零改动。
- **三档运行、无网也能演示**：真实 YouTube / 真 LLM+假数据 / 全离线打桩，没有 key 也能端到端跑通逻辑。
- **多格式输出 + Web UI + 一键脚本**：JSON/CSV/HTML 一次产出，运营用网页界面，开发用 `./start.sh`。
- **配套 Claude Code Skill**：装上后可用自然语言操控本工具（启动、跑查询、调阈值/权重），见下方[「可下载 Skill」](#claude-code-skill可下载)。

## 快速开始

一键脚本（自动建 venv / 装依赖 / 起服务）：

```bash
./start.sh                       # 启动 Web UI -> http://127.0.0.1:8000
./start.sh "想找居家健身方向的创作者"   # 跑一条真实 YouTube 查询
PROVIDER=mock ./start.sh "..."           # 真 LLM + 假数据，不耗 YouTube 配额
LLM_STUB=1 PROVIDER=mock ./start.sh "..."  # 全离线，不耗任何 key
```

或手动：

```bash
pip install -r requirements.txt
cp .env.example .env        # 填入 key（见下）

# 1) 无网络离线演示（mock 数据 + 打桩 LLM，验证全链路）
LLM_STUB=1 python run.py "我想找做居家健身、减脂训练和高蛋白饮食方向、粉丝量较大的优质创作者" --provider mock

# 2) 真实 LLM + mock 数据（验证 LLM 接通；不消耗 YouTube 配额）
python run.py "..." --provider mock

# 3) 真实 YouTube + 真实 LLM（端到端）
PROVIDER=youtube python run.py "..."

# Web UI（运营可直接使用）
uvicorn app:app --reload      # 打开 http://127.0.0.1:8000
```

输出写到 `out/results.{json,csv,html}`。

## 配置 key（`.env`）

| 变量 | 说明 |
| --- | --- |
| `SILICONFLOW_API_KEY` | LLM key（OpenAI 兼容；默认 SiliconFlow / DeepSeek） |
| `LLM_BASE_URL` | 默认 `https://api.siliconflow.cn/v1` |
| `LLM_MODEL` | 默认 `deepseek-ai/DeepSeek-V4-Flash`（快；可换 `DeepSeek-V4-Pro` 等任意 OpenAI 兼容模型） |
| `YOUTUBE_API_KEY` | YouTube Data API v3 密钥 |

验证 LLM 接通：`python -m media_scraper.llm --ping`（应回 `pong`）。

**申请 YouTube key**：[console.cloud.google.com](https://console.cloud.google.com) → 新建项目 → 库里启用 *YouTube Data API v3* → 凭据 → 创建 API 密钥。免费配额 1 万 units/天。

## 配置项（`config.yaml`）

筛选阈值/开关、召回宽度、排序权重、rubric 维度、去重折叠开关、不足 5 条策略——全部可配，无需改代码。

## 目录

```
media_scraper/
  pipeline.py            # 编排
  query_understanding.py # ① LLM 关键词扩展
  adapters/              # ② Platform Adapter 接口 + youtube + mock
  rules.py               # ③ 可配置规则筛选
  rank.py                # ④⑤ LLM 去重折叠 + 融合排序
  output.py              # ⑤ JSON/CSV/HTML
  llm.py / stub_llm.py   # LLM 客户端 / 离线打桩
run.py                   # CLI
app.py + web/index.html  # 极简 Web UI
config.yaml              # 全部可调参数
```

## Claude Code Skill（可下载）

本项目附带一个 Claude Code Skill，装上后可用**自然语言**操控本工具——「跑一下采集找做增肌餐的创作者」「把粉丝门槛提到 50 万」「结果不相关，调下权重」，Claude 自动选挡位、改 `config.yaml` 并重跑验证。

下载安装（[`skill/`](./skill) 目录）：

```bash
unzip skill/media-scraper-skill.zip -d ~/.claude/skills/   # 或 cp -r skill/media-scraper ~/.claude/skills/
```

重开会话即生效，详见 [`skill/README.md`](./skill/README.md)。

---

设计取舍与扩展规划见 [DESIGN.md](./DESIGN.md)。
