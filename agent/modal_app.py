"""Modal deployment of the concierge service (SPEC section 2).

One-time setup (owner):
  modal token new
  modal secret create meta-model-api MODEL_API_KEY=<key from dev.meta.ai> BASETEN_API_KEY=<Baseten hackathon key>
Then:
  modal serve  agent/modal_app.py     # hot-reloading dev URL
  modal deploy agent/modal_app.py     # stable *.modal.run URL for web/concierge.js

The image carries the agent package, cities/, scraper/ (the Resy client and the
venue-id cache live there) and web/ (config.js holds the public Supabase URL and
anon key that create_watch falls back to). Secrets come from the environment via
agent.config; add SUPABASE_URL / SUPABASE_ANON_KEY to the same Modal secret to
override the file.
"""
from __future__ import annotations

from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parents[1]

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("anthropic>=0.40,<3", "fastapi[standard]>=0.115", "python-multipart>=0.0.9",
                 "requests>=2.28", "tzdata")
    .env({"T42_PROMPTS_DIR": "/root/t42-prompts"})
    .add_local_dir(ROOT / "cities", remote_path="/root/cities")
    .add_local_dir(ROOT / "web", remote_path="/root/web")
    .add_local_dir(ROOT / "scraper", remote_path="/root/scraper",
                   ignore=["**/.ot_profile/**", "**/__pycache__/**", "**/*.lock", "**/*.log",
                           "**/.geocache.json", "**/.notify.json*"])
    .add_local_python_source("agent")
    # add_local_python_source ships .py only, and its /root/agent mount shadows
    # any file added into the same tree (missing system.md = 500 on /ask), so the
    # prompt template lives outside the package mount and config finds it via
    # T42_PROMPTS_DIR (agent.config; unset locally, where prompts/ sits beside
    # the code as before).
    .add_local_dir(ROOT / "agent" / "prompts", remote_path="/root/t42-prompts")
)

app = modal.App("table-for-two-concierge")


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("meta-model-api")],
    timeout=300,
    scaledown_window=120,
)
@modal.asgi_app()
def web():
    from agent.app import app as fastapi_app
    return fastapi_app
