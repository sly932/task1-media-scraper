"""环节 D —— LLM 去重折叠 + 融合排序 → Top5。

一次 LLM 调用同时完成（省 token）：
  - 语义相关性：对每个候选按 rubric 逐维判 Yes/No
  - 语义去重：给近似/搬运内容打同一个 dup_group 标签（规则去不掉的那种）
随后客观信号（views/likes/followers/recency）本地归一，不喂给 LLM；
final = semantic*w_sem + popularity*w_pop。
折叠：先按 dup_group 折叠搬运重复，再按创作者折叠（同账号留最强一条）。
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone

from .llm import LLMClient
from .schema import Candidate

SYSTEM = """[[TASK:rank]] 你是内容相关性评审。给定运营的查询、一组评审维度(rubric)，
和一批候选视频。请：
1) 对每个候选，按每个 rubric 维度判断是否满足(true/false)，顺序与维度一致；
2) 给语义上重复/搬运/雷同的内容打同一个 dup_group 标签(短字符串)，独一无二的内容给各自唯一标签；
3) 给一句不超过20字的中文相关性说明。
只输出 JSON：{"items":[{"id":"...","rubric":[true,false,...],"dup_group":"...","reason":"..."}]}"""


def score_and_rank(cands: list[Candidate], query: str, cfg: dict,
                   llm: LLMClient) -> list[Candidate]:
    if not cands:
        return []
    rubric = cfg["rubric"]
    weights = cfg["weights"]

    # ---- 1) LLM：语义相关性 + 去重标签（单次批量调用）----
    llm_map = _llm_relevance_dedup(cands, query, rubric, llm)

    # ---- 2) 客观信号归一（本地，不经 LLM）----
    _attach_popularity(cands, cfg["popularity_signals"])

    # ---- 3) 融合 final ----
    for c in cands:
        info = llm_map.get(c.content_id, {})
        hits = info.get("hits", [])
        c.rubric_hits = hits
        c.semantic_score = len(hits) / max(len(rubric), 1)
        c.final_score = (weights["semantic"] * c.semantic_score
                         + weights["popularity"] * c.popularity_score)
        why = info.get("reason", "")
        c.reason = (f"{why}｜命中{len(hits)}/{len(rubric)}维"
                    f"｜热度{c.popularity_score:.2f}")
        c._dup_group = info.get("dup_group", c.content_id)  # type: ignore

    # ---- 4) 去重折叠：dup_group -> 再 creator ----
    folded = _fold(cands, by="_dup_group")
    if cfg.get("fold_by_creator", True) and not cfg.get("allow_same_account", False):
        folded = _fold(folded, by="account_id")

    folded.sort(key=lambda c: c.final_score, reverse=True)
    return folded[: cfg["top_k"]]


def _llm_relevance_dedup(cands, query, rubric, llm) -> dict:
    payload = [{"id": c.content_id, "title": c.content_title,
                "desc": c.content_desc[:200], "account": c.account_name}
               for c in cands]
    user = ("查询：" + query
            + "\n维度(rubric)：" + json.dumps(rubric, ensure_ascii=False)
            + "\n候选：" + json.dumps(payload, ensure_ascii=False))
    data = llm.chat_json(SYSTEM, user)
    items = data.get("items", []) if isinstance(data, dict) else data
    out = {}
    for it in items:
        rb = it.get("rubric", [])
        hits = [rubric[i] for i, ok in enumerate(rb)
                if ok and i < len(rubric)]
        out[it["id"]] = {"hits": hits,
                         "dup_group": it.get("dup_group", it["id"]),
                         "reason": it.get("reason", "")}
    return out


def _attach_popularity(cands, sig_weights):
    now = datetime.now(timezone.utc)
    views = [c.views for c in cands]
    likes = [c.likes for c in cands]
    subs = [c.followers for c in cands]
    days = []
    for c in cands:
        dt = c.published_dt()
        days.append((now - dt).days if dt else 365)
    max_days = max(days) or 1

    wn = _normalize_weights(sig_weights)
    for i, c in enumerate(cands):
        nv = _log_norm(c.views, views)
        nl = _log_norm(c.likes, likes)
        ns = _log_norm(c.followers, subs)
        nr = 1 - (days[i] / max_days)  # 越新越高
        c.popularity_score = (wn["views"] * nv + wn["likes"] * nl
                              + wn["followers"] * ns + wn["recency"] * nr)


def _fold(cands, by: str) -> list[Candidate]:
    best: dict = {}
    for c in cands:
        k = getattr(c, by)
        if k not in best or c.final_score > best[k].final_score:
            best[k] = c
    return list(best.values())


def _log_norm(x, arr):
    lo, hi = min(arr), max(arr)
    if hi <= lo:
        return 1.0
    return (math.log(x + 1) - math.log(lo + 1)) / (math.log(hi + 1) - math.log(lo + 1))


def _normalize_weights(w: dict) -> dict:
    s = sum(w.values()) or 1
    return {k: v / s for k, v in w.items()}
