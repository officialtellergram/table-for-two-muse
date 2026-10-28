"""Offline tests for the voice route: Muse Voice Transcribe is stubbed."""
import json
import struct

import pytest
from fastapi.testclient import TestClient

from agent import app as service
from agent import planner, voice


def _wav(seconds=0.1, rate=16000):
    n = int(seconds * rate)
    data = b"\x00\x00" * n
    hdr = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVE" + b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
    return hdr + b"data" + struct.pack("<I", len(data)) + data


def test_rejects_non_wav(monkeypatch):
    with pytest.raises(voice.TranscribeError):
        voice.transcribe(b"not audio at all, just bytes that are long enough to pass the length check...")


def test_transcribe_posts_the_two_parts(monkeypatch):
    sent = {}

    class Resp:
        status_code = 200
        text = ""

        def json(self):
            return {"sessionId": "s1", "transcript": " Get four of us into Carbone ", "audioDurationMs": 4200,
                    "turns": [{"text": "x"}]}

    def fake_post(url, headers=None, files=None, timeout=None):
        sent.update(url=url, headers=headers, files=files)
        return Resp()

    import requests
    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(voice.config, "api_key", lambda: "k")
    r = voice.transcribe(_wav())
    assert r["transcript"] == "Get four of us into Carbone" and r["audio_ms"] == 4200 and r["turns"] == 1
    assert sent["url"].endswith("/v1/asr/transcribe") and sent["headers"]["Authorization"] == "Bearer k"
    req = json.loads(sent["files"]["request"][1])
    assert req == {"model": "muse-voice-transcribe-1.0", "audioEncoding": "WAV", "mode": "PUSH_TO_TALK"}
    assert sent["files"]["request"][2] == "application/json"
    assert sent["files"]["audio"][0].endswith(".wav") and sent["files"]["audio"][1][:4] == b"RIFF"


def test_voice_route_returns_transcript_for_editing(monkeypatch):
    monkeypatch.setattr(voice, "transcribe", lambda data, timeout=60.0: {"transcript": "Carbone Saturday", "audio_ms": 900,
                                                                        "session_id": "s", "turns": 1, "model": "m", "ms": 5})
    c = TestClient(service.app)
    r = c.post("/ask/voice", files={"audio": ("speech.wav", _wav(), "audio/wav")})
    assert r.status_code == 200 and r.json()["transcript"] == "Carbone Saturday"
    assert c.post("/ask/voice", files={"audio": ("speech.wav", b"", "audio/wav")}).status_code == 400


def test_voice_route_can_run_the_planner(monkeypatch):
    monkeypatch.setattr(voice, "transcribe", lambda data, timeout=60.0: {"transcript": "Carbone Saturday", "audio_ms": 900,
                                                                        "session_id": "s", "turns": 1, "model": "m", "ms": 5})

    def fake_run(message, city="nyc", model=None, max_rounds=None, now=None, ctx=None):
        yield {"type": "final", "text": f"NOW: {message}", "rounds": 1, "input_tokens": 1, "output_tokens": 1}

    monkeypatch.setattr(planner, "run", fake_run)
    c = TestClient(service.app)
    r = c.post("/ask/voice", files={"audio": ("speech.wav", _wav(), "audio/wav")}, data={"run": "true", "city": "nyc"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    types = [f.split("\n")[0].removeprefix("event: ") for f in r.text.split("\n\n") if f.strip()]
    assert types == ["transcript", "final"] and "Carbone Saturday" in r.text


def test_voice_failure_is_a_502(monkeypatch):
    def boom(data, timeout=60.0):
        raise voice.TranscribeError("voice API answered 401")

    monkeypatch.setattr(voice, "transcribe", boom)
    c = TestClient(service.app)
    r = c.post("/ask/voice", files={"audio": ("speech.wav", _wav(), "audio/wav")})
    assert r.status_code == 502 and "401" in r.json()["detail"]
