"""
Payments Route - Payment history and finance overview.
"""
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Optional

from app.admin.services.stats import StatsService

router = APIRouter(tags=["payments"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/payments", response_class=HTMLResponse)
async def payments_list(
    request: Request,
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1)
):
    """Payment history page."""
    payments = await StatsService.get_payments(status=status, page=page)
    revenue = await StatsService.get_revenue_stats()
    return templates.TemplateResponse("payments.html", {
        "request": request,
        "payments": payments.get("items", []),
        "total": payments.get("total", 0),
        "page": page,
        "status": status,
        "revenue": revenue,
        "active_page": "payments"
    })
