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
| `LLM_MODEL` | 默认 `deepseek-ai/DeepSeek-V4-Pro` |
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

设计取舍与扩展规划见 [DESIGN.md](./DESIGN.md)。
