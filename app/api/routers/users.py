from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.db.database import get_db
from app.api.schemas import UserCreate, UserRead
from app.api.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserRead)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    service = UserService() # Stateless
    return await service.create_user(db, user)

@router.get("/{telegram_id}", response_model=UserRead)
async def get_user_by_tg_id(telegram_id: int, db: AsyncSession = Depends(get_db)):
    service = UserService() 
    user = await service.get_user(db, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/{telegram_id}/subscription")
async def get_user_subscription(telegram_id: int, db: AsyncSession = Depends(get_db)):
    """Get detailed subscription info from Marzban"""
    service = UserService()
    sub_info = await service.get_user_subscription(db, telegram_id)
    if not sub_info:
        raise HTTPException(status_code=404, detail="Subscription not found in Marzban")
    return sub_info


# Server status endpoint (mounted at /server/status via main.py)
from app.api.services.xray import marzban_service

server_router = APIRouter(prefix="/server", tags=["server"])

@server_router.get("/status")
async def get_server_status():
    """Get Marzban server health status"""
    status = await marzban_service.get_server_status()
    return status
