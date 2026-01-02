"""
Servers Route - Server status monitoring page.
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.admin.services.marzban import MarzbanAdminService

router = APIRouter(tags=["servers"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/servers", response_class=HTMLResponse)
async def servers_status(request: Request):
    """Server status page."""
    status = await MarzbanAdminService.get_system_status()
    return templates.TemplateResponse("servers.html", {
        "request": request,
        "server": status,
        "active_page": "servers"
    })


@router.get("/api/servers/status")
async def api_server_status():
    """API endpoint for real-time server status."""
    return await MarzbanAdminService.get_system_status()
