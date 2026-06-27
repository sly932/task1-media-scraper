#!/usr/bin/env python3
"""CLI 入口：跑一次采集，产出 JSON/CSV/HTML。

  python run.py "想找居家健身、减脂的内容创作者"
  python run.py "..." --provider mock        # 无网络自测
  PROVIDER=youtube python run.py "..."        # 真实 YouTube
  LLM_STUB=1 python run.py "..."              # 离线打桩 LLM
"""
from __future__ import annotations

import argparse
import sys

from media_scraper.config import load_config
from media_scraper.output import write_all
from media_scraper.pipeline import run


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", help="自然语言查询（健身内容方向）")
    ap.add_argument("--provider", choices=["mock", "youtube"], help="覆盖 config")
    ap.add_argument("--config", default=None)
    ap.add_argument("--out", default="out")
    args = ap.parse_args()

    cfg = load_config(args.config)
    if args.provider:
        cfg["provider"] = args.provider

    res = run(args.query, cfg)

    print(f"\n查询：{res.query}")
    print(f"关键词：{res.keywords}")
    print(f"统计：{res.stats}\n")
    for r in res.results:
        print(f"  #{r.rank} [{r.relevance_score:.3f}] {r.account_name} "
              f"| {r.content_title[:42]} | 粉{r.followers:,} 播{r.views:,} 赞{r.likes:,}")
        print(f"        {r.reason}")
    if not res.results:
        print("  （无结果）", file=sys.stderr)

    outdir = write_all(res.results, args.out, res.query)
    print(f"\n输出已写入：{outdir}/results.[json|csv|html]")


if __name__ == "__main__":
    main()
