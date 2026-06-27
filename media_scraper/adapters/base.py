"""Platform Adapter 接口 —— 扩展到新平台只需实现这一个类。

约定的最小契约：
    search(keywords, limit)  -> 召回视频，回溯账号，返回 list[Candidate]
新增平台（抖音/TikTok/小红书）= 新写一个子类，pipeline / 规则 / 排序均不变。
"""
from __future__ import annotations

import abc

from ..schema import Candidate


class PlatformAdapter(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    def search(self, keywords: list[str], per_keyword: int,
               published_within_days: int = 0) -> list[Candidate]:
        """对每组关键词召回内容并 normalize 成 Candidate，去 content_id 重后返回并集。"""
        raise NotImplementedError


def get_adapter(provider: str) -> PlatformAdapter:
    if provider == "youtube":
        from .youtube import YouTubeAdapter
        return YouTubeAdapter()
    if provider == "mock":
        from .mock import MockAdapter
        return MockAdapter()
    raise ValueError(f"未知 provider: {provider}")
