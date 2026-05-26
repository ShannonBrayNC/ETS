from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="ETS Observatory")

BASE_DIR = Path(__file__).resolve().parent
SCENARIO_PATH = (
    Path(__file__).resolve().parents[3]
    / "experiments"
    / "scenarios"
    / "sprint11-replay-manifest.json"
)

TIMELINE = [
    {
        "tick": 1,
        "event": "evidence.appended",
        "node": "v1",
        "confidence": 0.91,
        "details": "Evidence committed into append-only state.",
    },
    {
        "tick": 2,
        "event": "root.gossip",
        "node": "v2",
        "confidence": 0.88,
        "details": "Verifier federation exchanged root observations.",
    },
    {
        "tick": 3,
        "event": "transport.replay.detected",
        "node": "v3",
        "confidence": 0.71,
        "details": "Replay visibility triggered bounded confidence degradation.",
    },
    {
        "tick": 4,
        "event": "partition.detected",
        "node": "v2",
        "confidence": 0.56,
        "details": "Selective visibility introduced epistemic asymmetry.",
    },
    {
        "tick": 5,
        "event": "omission.suspected",
        "node": "v1",
        "confidence": 0.48,
        "details": "Expected evidence propagation not observed across federation.",
    },
]


@app.get("/api/observatory/scenario")
def scenario() -> dict:
    return json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))


@app.get("/api/observatory/timeline")
def timeline() -> dict:
    return {"timeline": TIMELINE}


@app.get("/api/observatory/state")
def state() -> dict:
    latest = TIMELINE[-1]
    return {
        "federationState": "visibility-degraded",
        "confidence": latest["confidence"],
        "replayDetected": True,
        "omissionSuspicion": True,
        "partitionVisible": True,
        "activeVerifiers": ["v1", "v2", "v3"],
        "latestEvent": latest,
    }


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (BASE_DIR / "static" / "index.html").read_text(encoding="utf-8")
