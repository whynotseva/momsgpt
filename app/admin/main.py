"""
Admin Panel - Main FastAPI Application.
Premium dark-themed admin interface for MomsVPN management.
"""
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os

# App setup
app = FastAPI(
    title="MomsVPN Admin",
    docs_url="/admin/docs",
    redoc_url=None
)

# Paths
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Mount static files
app.mount("/admin/static", StaticFiles(directory=str(STATIC_DIR)), name="admin_static")

# Jinja2 templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# Import routes
from app.admin.routes import dashboard, users, keys, servers, payments

# Include routers
app.include_router(dashboard.router, prefix="/admin")
app.include_router(users.router, prefix="/admin")
app.include_router(keys.router, prefix="/admin")
app.include_router(servers.router, prefix="/admin")
app.include_router(payments.router, prefix="/admin")


@app.get("/admin", response_class=HTMLResponse)
async def admin_root(request: Request):
    """Redirect to dashboard."""
    return templates.TemplateResponse("dashboard.html", {"request": request})
