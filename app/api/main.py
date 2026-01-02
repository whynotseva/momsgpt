from fastapi import FastAPI
from app.api.db.database import engine, Base
import asyncio

app = FastAPI(
    title="VPN SaaS Core API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.on_event("startup")
async def startup():
    # Only for dev: create tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/")
async def root():
    return {"status": "ok", "service": "VPN SaaS Core API"}

from app.api.routers import users, billing, subscription
from app.api.routers.users import server_router

app.include_router(users.router)
app.include_router(billing.router)
app.include_router(subscription.router)
app.include_router(server_router)

# Mount Admin Panel
from app.admin.main import app as admin_app
app.mount("/admin", admin_app)
