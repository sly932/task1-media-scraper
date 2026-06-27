"""Mock 适配器 —— 从本地 fixture 召回，无需任何网络/key。

用途：无网络环境下端到端验证 pipeline 逻辑（规则/去重/排序/输出/UI）。
召回行为模拟：按关键词在标题/简介/账号名/简介里做大小写不敏感子串匹配，
取并集；关键词命中不到则放宽返回全部（模拟"宽召回"）。
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..schema import Candidate
from .base import PlatformAdapter

FIXTURE = Path(__file__).parent / "fixtures" / "mock_youtube.json"


class MockAdapter(PlatformAdapter):
    name = "mock"

    def __init__(self):
        with open(FIXTURE, "r", encoding="utf-8") as f:
            self._raw = json.load(f)

    def search(self, keywords: list[str], per_keyword: int,
               published_within_days: int = 0) -> list[Candidate]:
        # 把关键词拆成 token（模拟搜索引擎的分词召回，而非整串精确匹配）
        tokens: set[str] = set()
        for k in keywords:
            for t in k.lower().replace("-", " ").split():
                if len(t) >= 2 or _has_cjk(t):
                    tokens.add(t)
        picked: dict[str, dict] = {}
        for row in self._raw:
            blob = " ".join(str(row.get(k, "")) for k in
                            ("content_title", "content_desc",
                             "account_name", "account_bio")).lower()
            if not tokens or any(t in blob for t in tokens):
                picked[row["content_id"]] = row
        # 命中过少时放宽（模拟宽召回兜底）
        if len(picked) < 3:
            picked = {r["content_id"]: r for r in self._raw}

        now = datetime.now(timezone.utc)
        out: list[Candidate] = []
        for row in picked.values():
            pub = (now - timedelta(days=row["published_days_ago"])).isoformat()
            out.append(Candidate(
                platform="youtube",  # mock 模拟 youtube 数据形态
                content_id=row["content_id"],
                content_title=row["content_title"],
                content_desc=row["content_desc"],
                content_url=f"https://www.youtube.com/watch?v={row['content_id']}",
                views=row["views"],
                likes=row["likes"],
                published_at=pub,
                account_id=row["account_id"],
                account_name=row["account_name"],
                account_bio=row["account_bio"],
                account_url=f"https://www.youtube.com/channel/{row['account_id']}",
                followers=row["followers"],
                account_last_post_at=pub,
            ))
        return out[: max(per_keyword * len(keywords), len(out))]


def _has_cjk(s: str) -> bool:
    return any("一" <= ch <= "鿿" for ch in s)
