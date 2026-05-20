from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

_APP_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATES = _APP_ROOT / "templates"
_STATIC = _APP_ROOT / "static"

router = APIRouter()
templates = Jinja2Templates(directory=str(_TEMPLATES))


def mount_static(app) -> None:
    app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


@router.get("/{path:path}", response_class=HTMLResponse, include_in_schema=False)
async def ui_catchall(request: Request, path: str = ""):
    return templates.TemplateResponse(request, "index.html")
