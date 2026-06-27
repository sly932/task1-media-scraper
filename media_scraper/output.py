"""环节 E —— 标准化输出：JSON（机器可用）+ CSV/HTML（运营可直接看）。"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from .schema import MediaResult

FIELDS = ["rank", "platform", "account_name", "account_bio", "account_url",
          "content_title", "content_desc", "content_url",
          "followers", "views", "likes", "published_at",
          "relevance_score", "reason"]


def to_json(results: list[MediaResult]) -> str:
    return json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2)


def to_csv(results: list[MediaResult]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS)
    w.writeheader()
    for r in results:
        w.writerow({k: r.to_dict().get(k, "") for k in FIELDS})
    return buf.getvalue()


def to_html(results: list[MediaResult], query: str = "") -> str:
    rows = "".join(_row(r) for r in results)
    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>采集结果 Top{len(results)}</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:24px;color:#1d1d1f}}
 h1{{font-size:18px}} .q{{color:#666;margin-bottom:16px}}
 table{{border-collapse:collapse;width:100%;font-size:13px}}
 th,td{{border:1px solid #e3e3e3;padding:8px;text-align:left;vertical-align:top}}
 th{{background:#fafafa}} a{{color:#0066cc;text-decoration:none}}
 .num{{text-align:right;white-space:nowrap}} .rk{{font-weight:600}}
 .reason{{color:#888;font-size:12px}}
</style></head><body>
<h1>采集结果 · Top {len(results)}</h1>
<div class="q">查询：{_esc(query)}</div>
<table><thead><tr>
<th>#</th><th>账号</th><th>内容</th>
<th class="num">粉丝</th><th class="num">播放</th><th class="num">点赞</th>
<th>发布</th><th class="num">相关性</th></tr></thead>
<tbody>{rows}</tbody></table></body></html>"""


def _row(r: MediaResult) -> str:
    return (f"<tr><td class='rk'>{r.rank}</td>"
            f"<td><a href='{_esc(r.account_url)}' target='_blank'>{_esc(r.account_name)}</a>"
            f"<div class='reason'>{_esc(r.account_bio[:60])}</div></td>"
            f"<td><a href='{_esc(r.content_url)}' target='_blank'>{_esc(r.content_title)}</a>"
            f"<div class='reason'>{_esc(r.reason)}</div></td>"
            f"<td class='num'>{r.followers:,}</td>"
            f"<td class='num'>{r.views:,}</td>"
            f"<td class='num'>{r.likes:,}</td>"
            f"<td>{_esc((r.published_at or '')[:10])}</td>"
            f"<td class='num'>{r.relevance_score:.3f}</td></tr>")


def _esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def write_all(results: list[MediaResult], outdir: str | Path, query: str = ""):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "results.json").write_text(to_json(results), encoding="utf-8")
    (outdir / "results.csv").write_text(to_csv(results), encoding="utf-8")
    (outdir / "results.html").write_text(to_html(results, query), encoding="utf-8")
    return outdir
