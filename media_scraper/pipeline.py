"""Pipeline 编排：query → 召回 → 规则筛选 → LLM去重折叠+融合排序 → Top5。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .adapters import get_adapter
from .llm import make_llm
from .query_understanding import expand_keywords
from .rank import score_and_rank
from .rules import apply_filters
from .schema import Candidate, MediaResult


@dataclass
class PipelineResult:
    query: str
    results: list[MediaResult]
    keywords: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)


def run(query: str, cfg: dict) -> PipelineResult:
    llm = make_llm(cfg.get("llm", {}))
    adapter = get_adapter(cfg["provider"])
    rc = cfg["recall"]

    # B. query 理解 → 关键词
    keywords = expand_keywords(query, rc["keyword_groups"], llm)

    # 召回（宽，取并集，截上限控配额/token）
    cands = adapter.search(keywords, rc["per_keyword"], rc["published_within_days"])
    cands = _dedup_by_content(cands)[: rc["max_candidates"]]
    recalled = len(cands)

    # C. 规则筛选
    survivors, dropped = apply_filters(cands, cfg["filters"])

    # 不足策略
    relaxed = False
    if len(survivors) < cfg["ranking"]["top_k"] and cfg.get("shortfall_strategy") == "relax_filters":
        survivors = cands  # 放宽：跳过硬规则，让排序决定
        relaxed = True

    # D. LLM 去重折叠 + 融合排序 → Top5
    dedup_cfg = {**cfg["dedup"], **cfg["ranking"]}
    top = score_and_rank(survivors, query, dedup_cfg, llm)

    results = [MediaResult.from_candidate(c, rank=i + 1)
               for i, c in enumerate(top)]

    return PipelineResult(
        query=query, results=results, keywords=keywords,
        stats={"recalled": recalled, "after_filter": len(survivors),
               "dropped": len(dropped), "returned": len(results),
               "relaxed": relaxed, "provider": cfg["provider"],
               "llm_model": getattr(llm, "model", "?")},
    )


def _dedup_by_content(cands: list[Candidate]) -> list[Candidate]:
    seen, out = set(), []
    for c in cands:
        if c.content_id not in seen:
            seen.add(c.content_id)
            out.append(c)
    return out
