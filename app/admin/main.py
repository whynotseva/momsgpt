"""
Admin Panel - Main FastAPI Application.
Premium dark-themed admin interface for MomsVPN management.
"""
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pathlib import Path
import os
import secrets

# App setup
app = FastAPI(
    title="MomsVPN Admin",
    docs_url=None,  # Disable docs in production
    redoc_url=None
)

# HTTP Basic Auth
security = HTTPBasic()

# Admin credentials from environment (with defaults for dev)
ADMIN_USERNAME = os.getenv("ADMIN_PANEL_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PANEL_PASSWORD", "momsvpn_secure_2026")


def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify admin credentials with constant-time comparison."""
    correct_username = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# Paths
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Mount static files (no auth needed for CSS/JS)
app.mount("/admin/static", StaticFiles(directory=str(STATIC_DIR)), name="admin_static")

# Jinja2 templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# Import routes
from app.admin.routes import dashboard, users, keys, servers, payments

# Include routers with auth dependency
app.include_router(dashboard.router, prefix="/admin", dependencies=[Depends(verify_admin)])
app.include_router(users.router, prefix="/admin", dependencies=[Depends(verify_admin)])
app.include_router(keys.router, prefix="/admin", dependencies=[Depends(verify_admin)])
app.include_router(servers.router, prefix="/admin", dependencies=[Depends(verify_admin)])
app.include_router(payments.router, prefix="/admin", dependencies=[Depends(verify_admin)])


@app.get("/admin", response_class=HTMLResponse)
async def admin_root(request: Request, username: str = Depends(verify_admin)):
    """Redirect to dashboard (requires auth)."""
    return templates.TemplateResponse("dashboard.html", {"request": request, "username": username})

