"""YouTube Data API v3 适配器。

取数路径（控制请求数 / 配额）：
    search.list   -> 拿 videoId + channelId（每次 ~100 units）
    videos.list   -> 批量取 views/likes/publishedAt（每次 ~1 unit，最多 50 个/请求）
    channels.list -> 批量取 subscriberCount/简介（每次 ~1 unit，最多 50 个/请求）
含失败重试 + 限流退避。
"""
from __future__ import annotations

import time

import httpx

from ..config import env
from ..schema import Candidate
from .base import PlatformAdapter

API = "https://www.googleapis.com/youtube/v3"


class YouTubeAdapter(PlatformAdapter):
    name = "youtube"

    def __init__(self):
        self.key = env("YOUTUBE_API_KEY") or ""
        if not self.key:
            raise RuntimeError("未配置 YOUTUBE_API_KEY")
        self._client = httpx.Client(timeout=30)

    # ---- 带退避的 GET ----
    def _get(self, path: str, params: dict, retries: int = 3) -> dict:
        params = {**params, "key": self.key}
        for attempt in range(retries):
            r = self._client.get(f"{API}/{path}", params=params)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (403, 429, 500, 503) and attempt < retries - 1:
                time.sleep(2 ** attempt)  # 指数退避
                continue
            r.raise_for_status()
        return {}

    def search(self, keywords: list[str], per_keyword: int,
               published_within_days: int = 0) -> list[Candidate]:
        published_after = None
        if published_within_days > 0:
            from datetime import datetime, timedelta, timezone
            published_after = (datetime.now(timezone.utc)
                               - timedelta(days=published_within_days)
                               ).strftime("%Y-%m-%dT%H:%M:%SZ")

        video_ids: list[str] = []
        vid2channel: dict[str, str] = {}
        for kw in keywords:
            params = {
                "part": "snippet", "q": kw, "type": "video",
                "maxResults": min(per_keyword, 50), "order": "relevance",
            }
            if published_after:
                params["publishedAfter"] = published_after
            data = self._get("search", params)
            for item in data.get("items", []):
                vid = item["id"]["videoId"]
                if vid not in vid2channel:
                    video_ids.append(vid)
                    vid2channel[vid] = item["snippet"]["channelId"]

        if not video_ids:
            return []

        videos = self._batch("videos", video_ids,
                              part="snippet,statistics")
        channel_ids = list({v["snippet"]["channelId"] for v in videos})
        channels = {c["id"]: c for c in
                    self._batch("channels", channel_ids, part="snippet,statistics")}

        out: list[Candidate] = []
        for v in videos:
            sn, st = v["snippet"], v.get("statistics", {})
            ch = channels.get(sn["channelId"], {})
            csn, cst = ch.get("snippet", {}), ch.get("statistics", {})
            out.append(Candidate(
                platform="youtube",
                content_id=v["id"],
                content_title=sn.get("title", ""),
                content_desc=sn.get("description", ""),
                content_url=f"https://www.youtube.com/watch?v={v['id']}",
                views=_int(st.get("viewCount")),
                likes=_int(st.get("likeCount")),       # 部分视频隐藏 -> 0 兜底
                published_at=sn.get("publishedAt"),
                account_id=sn["channelId"],
                account_name=csn.get("title", sn.get("channelTitle", "")),
                account_bio=csn.get("description", ""),
                account_url=f"https://www.youtube.com/channel/{sn['channelId']}",
                followers=_int(cst.get("subscriberCount")),
                account_last_post_at=sn.get("publishedAt"),
            ))
        return out

    def _batch(self, path: str, ids: list[str], **params) -> list[dict]:
        """videos/channels.list 一次最多 50 个 id。"""
        items: list[dict] = []
        for i in range(0, len(ids), 50):
            chunk = ids[i:i + 50]
            data = self._get(path, {**params, "id": ",".join(chunk)})
            items.extend(data.get("items", []))
        return items


def _int(x) -> int:
    try:
        return int(x)
    except (TypeError, ValueError):
        return 0
