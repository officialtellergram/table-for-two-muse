"""Paths, model names and the Meta Model API key.

Key resolution order (first hit wins):
  1. MODEL_API_KEY            - the name used for the Modal secret (SPEC section 9)
  2. ANTHROPIC_AUTH_TOKEN     - what the Claude Code launcher exports
  3. .claude/settings.local.json -> env.ANTHROPIC_AUTH_TOKEN (git-ignored, local dev only)
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(os.environ.get("T42_ROOT") or Path(__file__).resolve().parents[1])
CITIES_DIR = ROOT / "cities"
SCRAPER_DIR = ROOT / "scraper"
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

META_BASE_URL = os.environ.get("META_BASE_URL", "https://api.meta.ai")
PLANNER_MODEL = os.environ.get("MUSE_MODEL", "muse-wonder-1.0")
FALLBACK_MODEL = os.environ.get("MUSE_FALLBACK_MODEL", "muse-spark-1.3")
# Thinking tokens count against max_tokens on Muse (SPEC section 4): keep headroom.
MAX_TOKENS = int(os.environ.get("MUSE_MAX_TOKENS", "2000"))
MAX_TOOL_ROUNDS = int(os.environ.get("MUSE_MAX_TOOL_ROUNDS", "12"))


def api_key() -> str:
    for name in ("MODEL_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        v = os.environ.get(name)
        if v:
            return v
    local = ROOT / ".claude" / "settings.local.json"
    if local.exists():
        try:
            env = json.loads(local.read_text(encoding="utf-8")).get("env", {})
            v = env.get("MODEL_API_KEY") or env.get("ANTHROPIC_AUTH_TOKEN")
            if v:
                return v
        except (OSError, ValueError):
            pass
    raise RuntimeError(
        "No Meta Model API key. Set MODEL_API_KEY (or ANTHROPIC_AUTH_TOKEN), "
        "or keep it in .claude/settings.local.json for local runs."
    )
