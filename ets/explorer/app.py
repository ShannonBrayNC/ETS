import os
from pathlib import Path
from typing import Any, cast

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

APP_ROOT = Path(__file__).resolve().parent
TEMPLATES_DIR = APP_ROOT / "templates"
STATIC_DIR = APP_ROOT / "static"
API_BASE_URL = os.getenv("ETS_API_BASE_URL", "http://localhost:8000")

app = FastAPI(
    title="ETS Explorer",
    version="0.1.0",
    description="Reference explorer interface for browsing ETS log events and proofs.",
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


async def api_get(path: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(f"{API_BASE_URL}{path}")
        response.raise_for_status()
        return cast(dict[str, Any], response.json())


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {
        "status": "ok",
        "api_base_url": API_BASE_URL,
    }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    tree_head: dict[str, Any] | None = None
    events: list[dict[str, Any]] = []
    api_error: str | None = None

    try:
        tree_head = await api_get("/api/v1/log/head")
        if tree_head.get("tree_size", 0) > 0:
            # Reference implementation fallback: probe recent events from a simple integer range.
            # This keeps the explorer useful even before a list endpoint exists.
            pass
    except Exception as ex:
        api_error = str(ex)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "api_base_url": API_BASE_URL,
            "tree_head": tree_head,
            "events": events,
            "api_error": api_error,
        },
    )
