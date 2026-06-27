"""环节 C —— 规则筛选（可配置，先于 LLM）。

账号级 + 内容级硬规则，把候选从几十/上百降到几十，便宜且稳定。
每条规则可单独 enabled 开关、阈值可配。返回幸存候选 + 被筛原因（可观测）。
"""
from __future__ import annotations

from datetime import datetime, timezone

from .schema import Candidate


def apply_filters(cands: list[Candidate], cfg: dict) -> tuple[list[Candidate], list[dict]]:
    acc = cfg["account"]
    con = cfg["content"]
    now = datetime.now(timezone.utc)

    survivors: list[Candidate] = []
    dropped: list[dict] = []
    for c in cands:
        reasons = []

        if acc["min_followers"]["enabled"] and c.followers < acc["min_followers"]["value"]:
            reasons.append(f"followers<{acc['min_followers']['value']}")

        if acc["last_post_within_days"]["enabled"]:
            dt = c.last_post_dt()
            days = (now - dt).days if dt else 10**6
            if days > acc["last_post_within_days"]["value"]:
                reasons.append(f"last_post>{acc['last_post_within_days']['value']}d")

        if con["min_views"]["enabled"] and c.views < con["min_views"]["value"]:
            reasons.append(f"views<{con['min_views']['value']}")

        if con["min_likes"]["enabled"] and c.likes < con["min_likes"]["value"]:
            reasons.append(f"likes<{con['min_likes']['value']}")

        if reasons:
            dropped.append({"content_id": c.content_id,
                            "title": c.content_title, "why": reasons})
        else:
            survivors.append(c)
    return survivors, dropped
