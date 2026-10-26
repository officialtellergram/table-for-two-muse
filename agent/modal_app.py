"""Modal deployment of the concierge service (SPEC section 2).

One-time setup (owner):
  modal token new
  modal secret create meta-model-api MODEL_API_KEY=<key from dev.meta.ai>
Then:
  modal serve  agent/modal_app.py     # hot-reloading dev URL
  modal deploy agent/modal_app.py     # stable *.modal.run URL for web/concierge.js

The image carries the agent package, cities/ and scraper/ (the Resy client lives
there; phase 2 calls it). Secrets are read from the environment by agent.config.
"""
from __future__ import annotations

from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parents[1]

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("anthropic>=0.40,<3", "fastapi[standard]>=0.115", "requests>=2.28", "tzdata")
    .add_local_dir(ROOT / "cities", remote_path="/root/cities")
    .add_local_dir(ROOT / "scraper", remote_path="/root/scraper",
                   ignore=["**/.ot_profile/**", "**/__pycache__/**", "**/*.lock", "**/*.log",
                           "**/.geocache.json", "**/.notify.json*"])
    .add_local_python_source("agent")
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
