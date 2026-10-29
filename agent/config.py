"""Paths, model names and the Meta Model API key.

Key resolution order (first hit wins):
  1. MODEL_API_KEY            - the name used for the Modal secret (SPEC section 9)
  2. ANTHROPIC_AUTH_TOKEN     - what the Claude Code launcher exports
  3. .claude/settings.local.json -> env.ANTHROPIC_AUTH_TOKEN (git-ignored, local dev only)
The Baseten key (open weights, agent.openweights) resolves the same way under
BASETEN_API_KEY.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(os.environ.get("T42_ROOT") or Path(__file__).resolve().parents[1])
CITIES_DIR = ROOT / "cities"
SCRAPER_DIR = ROOT / "scraper"
PROMPTS_DIR = Path(os.environ.get("T42_PROMPTS_DIR") or Path(__file__).resolve().parent / "prompts")

META_BASE_URL = os.environ.get("META_BASE_URL", "https://api.meta.ai")
PLANNER_MODEL = os.environ.get("MUSE_MODEL", "muse-wonder-1.0")
FALLBACK_MODEL = os.environ.get("MUSE_FALLBACK_MODEL", "muse-spark-1.3")
# Thinking tokens count against max_tokens on Muse (SPEC section 4): keep headroom.
MAX_TOKENS = int(os.environ.get("MUSE_MAX_TOKENS", "2000"))
MAX_TOOL_ROUNDS = int(os.environ.get("MUSE_MAX_TOOL_ROUNDS", "12"))

# Open weights (SPEC section 6, revised 28 Oct): Muse Spark Open served per-token by
# Baseten's Model API for the hackathon (OpenAI chat-completions shape). The planner
# routes model "spark-open" (or the full slug) through agent.openweights when
# OPENWEIGHTS=baseten; OPENWEIGHTS=off refuses it. The hackathon key only works with
# the "-1026" slug, so keep OPENWEIGHTS_MODEL exactly as Baseten's welcome mail says.
OPENWEIGHTS = os.environ.get("OPENWEIGHTS", "baseten")
BASETEN_BASE_URL = os.environ.get("BASETEN_BASE_URL", "https://inference.baseten.co/v1")
OPENWEIGHTS_MODEL = os.environ.get("OPENWEIGHTS_MODEL", "meta-models/muse-spark-open-1026")
OPENWEIGHTS_ALIASES = {"spark-open", "openweights", "open-weights", "baseten"}
# Spark Open always reasons; xhigh is the default and slow. low keeps a tool round quick.
OPENWEIGHTS_EFFORT = os.environ.get("OPENWEIGHTS_EFFORT", "low")
# Reasoning tokens count against completion tokens, so this is roomier than MAX_TOKENS.
OPENWEIGHTS_MAX_TOKENS = int(os.environ.get("OPENWEIGHTS_MAX_TOKENS", "4000"))


def is_openweights_model(model: str | None) -> bool:
    m = (model or "").strip().lower()
    return m in OPENWEIGHTS_ALIASES or m == OPENWEIGHTS_MODEL.lower() or m.startswith("meta-models/")


def _local_env() -> dict[str, str]:
    """The env block of the git-ignored .claude/settings.local.json (local dev only)."""
    local = ROOT / ".claude" / "settings.local.json"
    if not local.exists():
        return {}
    try:
        return json.loads(local.read_text(encoding="utf-8")).get("env", {}) or {}
    except (OSError, ValueError):
        return {}


def api_key() -> str:
    for name in ("MODEL_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        v = os.environ.get(name)
        if v:
            return v
    env = _local_env()
    v = env.get("MODEL_API_KEY") or env.get("ANTHROPIC_AUTH_TOKEN")
    if v:
        return v
    raise RuntimeError(
        "No Meta Model API key. Set MODEL_API_KEY (or ANTHROPIC_AUTH_TOKEN), "
        "or keep it in .claude/settings.local.json for local runs."
    )


def baseten_key() -> str:
    """Baseten API key: BASETEN_API_KEY in the environment (the Modal secret) or in the
    env block of .claude/settings.local.json next to the Muse key."""
    v = os.environ.get("BASETEN_API_KEY") or _local_env().get("BASETEN_API_KEY")
    if v:
        return v
    raise RuntimeError(
        "No Baseten API key. Set BASETEN_API_KEY (add it to the meta-model-api Modal "
        "secret), or keep it in .claude/settings.local.json for local runs."
    )


def has_baseten_key() -> bool:
    try:
        baseten_key()
        return True
    except RuntimeError:
        return False
