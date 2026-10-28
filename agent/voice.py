"""Muse Voice Transcribe: one WAV in, a transcript out (SPEC sections 4 and 5).

POST https://api.meta.ai/v1/asr/transcribe is multipart with two parts:
`request` (JSON: model, audioEncoding, mode) and `audio` (WAV, mono 16-bit,
16 or 24 kHz, up to 10 minutes / 32 MB). The response carries `transcript`,
`audioDurationMs`, `sessionId` and `turns`. The voice model is only reachable
here, not through /v1/messages, so this is a plain requests call rather than
the Anthropic SDK the planner uses.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any

from . import config

ASR_URL = f"{config.META_BASE_URL}/v1/asr/transcribe"
ASR_MODEL = os.environ.get("MUSE_ASR_MODEL", "muse-voice-transcribe-1.0")
MAX_BYTES = 32 * 1024 * 1024


class TranscribeError(RuntimeError):
    pass


def is_wav(data: bytes) -> bool:
    return len(data) > 44 and data[:4] == b"RIFF" and data[8:12] == b"WAVE"


def transcribe(wav: bytes, timeout: float = 60.0) -> dict[str, Any]:
    """Transcript for one WAV payload. Raises TranscribeError with a plain reason."""
    if not is_wav(wav):
        raise TranscribeError("audio must be a WAV file (RIFF/WAVE), mono 16-bit, 16 or 24 kHz")
    if len(wav) > MAX_BYTES:
        raise TranscribeError("audio is over the 32 MB limit")
    import requests
    req = {"model": ASR_MODEL, "audioEncoding": "WAV", "mode": "PUSH_TO_TALK"}
    t0 = time.time()
    try:
        r = requests.post(
            ASR_URL,
            headers={"Authorization": f"Bearer {config.api_key()}"},
            files={"request": (None, json.dumps(req), "application/json"),
                   "audio": ("audio.wav", wav, "audio/wav")},
            timeout=timeout,
        )
    except requests.RequestException as e:
        raise TranscribeError(f"voice API unreachable: {e}") from e
    if r.status_code != 200:
        raise TranscribeError(f"voice API answered {r.status_code}: {r.text[:200]}")
    try:
        d = r.json()
    except ValueError as e:
        raise TranscribeError("voice API returned a non-JSON body") from e
    return {
        "transcript": (d.get("transcript") or "").strip(),
        "audio_ms": d.get("audioDurationMs"),
        "session_id": d.get("sessionId"),
        "turns": len(d.get("turns") or []),
        "model": ASR_MODEL,
        "ms": int((time.time() - t0) * 1000),
    }
