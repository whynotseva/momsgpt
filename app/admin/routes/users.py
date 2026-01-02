"""
Users Route - User management page.
"""
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Optional

from app.admin.services.stats import StatsService

router = APIRouter(tags=["users"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/users", response_class=HTMLResponse)
async def users_list(
    request: Request,
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1)
):
    """List all users with search and filters."""
    users = await StatsService.get_users(search=search, status=status, page=page)
    return templates.TemplateResponse("users.html", {
        "request": request,
        "users": users.get("items", []),
        "total": users.get("total", 0),
        "page": page,
        "search": search,
        "status": status,
        "active_page": "users"
    })


@router.get("/users/{telegram_id}", response_class=HTMLResponse)
async def user_detail(request: Request, telegram_id: int):
    """User detail page."""
    user = await StatsService.get_user_detail(telegram_id)
    return templates.TemplateResponse("user_detail.html", {
        "request": request,
        "user": user,
        "active_page": "users"
    })
