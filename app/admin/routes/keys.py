"""
Keys Route - VPN key management page.
"""
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.admin.services.marzban import MarzbanAdminService

router = APIRouter(tags=["keys"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/keys", response_class=HTMLResponse)
async def keys_list(request: Request):
    """List all VPN keys."""
    keys = await MarzbanAdminService.get_all_users()
    return templates.TemplateResponse("keys.html", {
        "request": request,
        "keys": keys,
        "active_page": "keys"
    })


@router.post("/keys/{username}/block")
async def block_key(username: str):
    """Block a VPN key."""
    await MarzbanAdminService.disable_user(username)
    return RedirectResponse(url="/admin/keys", status_code=303)


@router.post("/keys/{username}/unblock")
async def unblock_key(username: str):
    """Unblock a VPN key."""
    await MarzbanAdminService.enable_user(username)
    return RedirectResponse(url="/admin/keys", status_code=303)


@router.post("/keys/{username}/reset-traffic")
async def reset_traffic(username: str):
    """Reset traffic for a key."""
    await MarzbanAdminService.reset_user_traffic(username)
    return RedirectResponse(url="/admin/keys", status_code=303)


@router.post("/keys/{username}/extend")
async def extend_key(username: str, days: int = Form(...)):
    """Extend key expiration."""
    await MarzbanAdminService.extend_user(username, days)
    return RedirectResponse(url="/admin/keys", status_code=303)
