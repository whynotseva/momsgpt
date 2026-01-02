"""
Dashboard Route - Main admin page with statistics.
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.admin.services.stats import StatsService

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard with statistics."""
    stats = await StatsService.get_overview()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats,
        "active_page": "dashboard"
    })
