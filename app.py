#!/usr/bin/env python3
"""极简 Web UI —— 运营可直接使用：输入 query → 跑 pipeline → 表格展示 Top5。

  uvicorn app:app --reload      然后访问 http://127.0.0.1:8000
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse

from media_scraper.config import load_config
from media_scraper.pipeline import run

app = FastAPI(title="Media Scraper")
INDEX = (Path(__file__).parent / "web" / "index.html").read_text(encoding="utf-8")


@app.get("/", response_class=HTMLResponse)
def index():
    return INDEX


@app.post("/api/search")
def search(query: str = Form(...), provider: str = Form("")):
    cfg = load_config()
    if provider:
        cfg["provider"] = provider
    res = run(query, cfg)
    return JSONResponse({
        "query": res.query,
        "keywords": res.keywords,
        "stats": res.stats,
        "results": [r.to_dict() for r in res.results],
    })
