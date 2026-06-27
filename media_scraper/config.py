"""配置加载：config.yaml + .env。"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    load_dotenv(ROOT / ".env")
    cfg_path = Path(path) if path else ROOT / "config.yaml"
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    # 环境变量覆盖 provider（方便命令行/UI 临时切换）
    if os.getenv("PROVIDER"):
        cfg["provider"] = os.getenv("PROVIDER")
    return cfg


def env(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)
