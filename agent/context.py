"""Per-request state shared by the planner and the tools that need it.

One RequestContext is created per planner run (agent.planner.run) and handed to
tools.call(); tools that declare a `_ctx` keyword receive it. It carries the
live-Resy call budget (SPEC section 3: hard cap of four Resy calls per request)
and, from phase 2 onwards, the guest's Supabase access token for create_watch.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

RESY_CALLS_PER_REQUEST = int(os.environ.get("T42_RESY_CALLS_PER_REQUEST", "4"))


class Budget:
    """Counts Resy HTTP calls for one request. Cache hits never consume it."""

    def __init__(self, limit: int = RESY_CALLS_PER_REQUEST) -> None:
        self.limit = max(0, int(limit))
        self.used = 0

    @property
    def left(self) -> int:
        return max(0, self.limit - self.used)

    def take(self) -> bool:
        if self.used >= self.limit:
            return False
        self.used += 1
        return True

    def as_dict(self) -> dict[str, int]:
        return {"resy_calls_used": self.used, "resy_calls_left": self.left}


@dataclass
class RequestContext:
    resy_budget: Budget = field(default_factory=Budget)
    user_token: str | None = None     # Supabase access token of a signed-in guest, if any
    city: str = "nyc"
