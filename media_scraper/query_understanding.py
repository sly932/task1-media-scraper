"""环节 B —— query 理解：LLM 把自然语言 query 扩成多组搜索关键词。

健身类英文素材多，要求中英文都扩，提升 YouTube 召回覆盖。
返回去重后的关键词列表（截断到 keyword_groups）。
"""
from __future__ import annotations

from .llm import LLMClient

SYSTEM = """[[TASK:keywords]] 你是内容运营的搜索助手。
把运营给的自然语言需求，扩展成适合在视频平台搜索框直接使用的关键词。
要求：覆盖中英文；既有宽词也有具体词；每个关键词是真实会被搜索的短语。
输出 JSON：{"keywords": ["...", "..."]}"""


def expand_keywords(query: str, n: int, llm: LLMClient) -> list[str]:
    user = f"运营需求：{query}\n请扩展出约 {n} 个搜索关键词。"
    data = llm.chat_json(SYSTEM, user)
    kws = data.get("keywords", []) if isinstance(data, dict) else list(data)
    # 去重保序 + 截断
    seen, out = set(), []
    for k in kws:
        k = str(k).strip()
        if k and k.lower() not in seen:
            seen.add(k.lower())
            out.append(k)
    return out[:n] or [query]
