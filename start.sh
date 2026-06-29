#!/usr/bin/env bash
# 一键启动 media-scraper。
#   ./start.sh                 启动 Web UI（http://127.0.0.1:8000）
#   ./start.sh "需求那句话"      跑一条真实 YouTube 查询（CLI）
#   PROVIDER=mock ./start.sh "..."   用假数据，不耗 YouTube 配额
#   LLM_STUB=1 PROVIDER=mock ./start.sh "..."   全离线，不耗任何 key
set -euo pipefail
cd "$(dirname "$0")"

# 1) 准备虚拟环境 + 依赖（只在缺失时做）
if [ ! -d .venv ]; then
  echo "[start] 创建虚拟环境 .venv ..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
if ! python -c "import fastapi" 2>/dev/null; then
  echo "[start] 安装依赖 ..."
  pip install -q -r requirements.txt
fi

# 2) 检查 .env
if [ ! -f .env ]; then
  cp .env.example .env
  echo "[start] 已从 .env.example 生成 .env —— 请先填好 SILICONFLOW_API_KEY / YOUTUBE_API_KEY 再运行真实查询。"
fi

PROVIDER="${PROVIDER:-youtube}"

# 3) 有参数 -> 跑一条查询；无参数 -> 起 Web UI
if [ "$#" -ge 1 ]; then
  echo "[start] 查询：${1} (provider=${PROVIDER})"
  PROVIDER="${PROVIDER}" python run.py "$1"
else
  echo "[start] Web UI 启动中 -> http://127.0.0.1:8000  (Ctrl+C 退出)"
  exec uvicorn app:app --reload
fi
