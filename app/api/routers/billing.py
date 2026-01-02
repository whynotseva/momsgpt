from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.db.database import get_db
from app.api.schemas import PaymentInit, PaymentResponse
from app.api.services.billing import BillingService
from app.api.services.user_service import UserService

router = APIRouter(prefix="/billing", tags=["billing"])

@router.post("/pay/{telegram_id}", response_model=PaymentResponse)
async def init_payment(telegram_id: int, payment_data: PaymentInit, db: AsyncSession = Depends(get_db)):
    user_service = UserService(db)
    user = await user_service.get_user(telegram_id)
    if not user:
        # Auto-create user if not exists (optional, depends on flow)
        # For now, simplistic approach
        from app.api.schemas import UserCreate
        user = await user_service.create_user(UserCreate(telegram_id=telegram_id))

    service = BillingService(db)
    url, pid = await service.create_payment(user.id, payment_data)
    
    return PaymentResponse(payment_url=url, payment_id=pid)

@router.post("/webhook/yookassa")
async def yookassa_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()
    service = BillingService(db)
    # Process webhook logic (simplified)
    await service.process_webhook(data)
    return {"status": "ok"}
