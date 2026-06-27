"""离线打桩 LLM —— 仅用于无网络自测（LLM_STUB=1）。

不联网，按启发式规则模拟 LLM 在两类任务上的结构化输出：
  [[TASK:keywords]] -> 返回一组中英文健身关键词
  [[TASK:rank]]     -> 按词命中模拟 rubric 判定 + dup_group + reason
真实运行请用 LLMClient（DeepSeek/SiliconFlow）。
"""
from __future__ import annotations

import json
import re

_FIT = ["workout", "fitness", "hiit", "training", "muscle", "fat loss",
        "home", "dumbbell", "stretch", "mobility", "nutrition", "meal",
        "recipe", "protein", "健身", "减脂", "燃脂", "训练", "居家", "食谱", "减肥"]
_AUDIENCE = ["beginner", "home", "居家", "宅家", "零基础", "fat loss", "减脂", "low impact"]
_FORM = ["routine", "workout", "跟练", "操", "recipe", "食谱", "meal", "training", "训练"]
_CREDIBLE = ["science", "evidence", "nutrition", "phd", "研究", "专注", "专业", "营养"]


class StubLLMClient:
    model = "stub"
    base_url = "stub://offline"
    api_key = "stub"

    def chat_json(self, system: str, user: str, **kw):
        if "[[TASK:keywords]]" in system:
            return {"keywords": ["home workout", "fat loss workout", "HIIT 居家",
                                 "减脂 training", "高蛋白 食谱", "no equipment workout",
                                 "燃脂 跟练"]}
        if "[[TASK:rank]]" in system:
            return self._rank(user)
        return {}

    def _rank(self, user: str):
        cands = _last_json_array(user)
        rubric = _first_json_array(user)
        items = []
        for c in cands:
            blob = f"{c.get('title','')} {c.get('desc','')} {c.get('account','')}".lower()
            dims = [
                any(t in blob for t in _FIT),
                any(t in blob for t in _AUDIENCE),
                any(t in blob for t in _FORM),
                any(t in blob for t in _CREDIBLE),
            ][: len(rubric)]
            hits = sum(dims)
            reason = "高度相关" if hits >= 3 else ("相关" if hits == 2 else "弱相关")
            items.append({"id": c["id"], "rubric": dims,
                          "dup_group": c["id"], "reason": reason})
        return {"items": items}

    def ping(self):
        return "pong(stub)"


def _last_json_array(text: str):
    arrs = re.findall(r"\[.*?\]", text, re.S)
    for a in reversed(arrs):
        try:
            v = json.loads(a)
            if v and isinstance(v[0], dict):
                return v
        except Exception:
            continue
    return []


def _first_json_array(text: str):
    for a in re.findall(r"\[.*?\]", text, re.S):
        try:
            v = json.loads(a)
            if v and isinstance(v[0], str):
                return v
        except Exception:
            continue
    return ["d1", "d2", "d3", "d4"]
