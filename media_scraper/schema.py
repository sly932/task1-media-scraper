"""统一数据 schema —— 跨平台对齐的字段定义。

所有 Platform Adapter 都把原始数据 normalize 成 Candidate；
最终输出 MediaResult（题目要求的 Top5 字段）。
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Candidate:
    """召回 + normalize 后的统一候选（视频为主体，回溯账号）。"""
    platform: str
    # 内容（视频）
    content_id: str
    content_title: str
    content_desc: str
    content_url: str
    views: int
    likes: int
    published_at: Optional[str]          # ISO8601
    # 账号（频道）
    account_id: str
    account_name: str
    account_bio: str
    account_url: str
    followers: int
    account_last_post_at: Optional[str] = None  # 账号最新内容时间，供账号级筛选

    # pipeline 过程中填充
    semantic_score: float = 0.0
    popularity_score: float = 0.0
    final_score: float = 0.0
    rubric_hits: list[str] = field(default_factory=list)
    reason: str = ""

    def published_dt(self) -> Optional[datetime]:
        return _parse_dt(self.published_at)

    def last_post_dt(self) -> Optional[datetime]:
        return _parse_dt(self.account_last_post_at or self.published_at)


@dataclass
class MediaResult:
    """题目要求的最终输出字段（每条 Top5）。"""
    platform: str
    account_name: str
    account_bio: str
    account_url: str
    content_title: str
    content_desc: str
    content_url: str
    followers: int
    views: int
    likes: int
    published_at: Optional[str]
    # 附加：可解释性（nice-to-have，运营判断用）
    rank: int = 0
    relevance_score: float = 0.0
    reason: str = ""

    @classmethod
    def from_candidate(cls, c: Candidate, rank: int) -> "MediaResult":
        return cls(
            platform=c.platform,
            account_name=c.account_name,
            account_bio=c.account_bio,
            account_url=c.account_url,
            content_title=c.content_title,
            content_desc=c.content_desc,
            content_url=c.content_url,
            followers=c.followers,
            views=c.views,
            likes=c.likes,
            published_at=c.published_at,
            rank=rank,
            relevance_score=round(c.final_score, 4),
            reason=c.reason,
        )

    def to_dict(self) -> dict:
        return asdict(self)


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None
