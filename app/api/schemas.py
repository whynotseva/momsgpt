from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# User Schemas
class UserBase(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    full_name: Optional[str] = None

class UserCreate(UserBase):
    pass

class UserRead(UserBase):
    id: int
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Subscription Schemas
class SubscriptionRead(BaseModel):
    is_active: bool
    expires_at: Optional[datetime]

# Billing Schemas
class PaymentInit(BaseModel):
    amount: float
    description: str

class PaymentResponse(BaseModel):
    payment_url: str
    payment_id: str
