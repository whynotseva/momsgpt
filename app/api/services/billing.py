from yookassa import Configuration, Payment
from app.api.db.database import AsyncSession
from app.api.models import Transaction, User
from app.api.schemas import PaymentInit
import uuid
import os

# Init Yookassa
Configuration.account_id = os.getenv("YOOKASSA_SHOP_ID")
Configuration.secret_key = os.getenv("YOOKASSA_SECRET_KEY")

class BillingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_payment(self, user_id: int, payment_data: PaymentInit):
        idempotence_key = str(uuid.uuid4())
        
        # Create payment in Yookassa
        payment = Payment.create({
            "amount": {
                "value": f"{payment_data.amount:.2f}",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": "https://t.me/your_bot_name" # Should be dynamic or env var
            },
            "capture": True,
            "description": payment_data.description,
            "metadata": {
                "user_id": user_id
            }
        }, idempotence_key)

        # Save pending transaction to DB
        transaction = Transaction(
            user_id=user_id,
            amount=int(payment_data.amount * 100), # Store in kopecks
            currency="RUB",
            provider_payment_id=payment.id,
            status="pending"
        )
        self.db.add(transaction)
        await self.db.commit()

        return payment.confirmation.confirmation_url, payment.id
    
    async def process_webhook(self, event_json: dict):
        # Yookassa sends events like payment.succeeded
        if event_json.get("type") == "notification" and event_json.get("event") == "payment.succeeded":
            obj = event_json.get("object", {})
            payment_id = obj.get("id")
            
            # Find transaction
            # In real async app, we would query the DB. 
            # Note: For simplicity in this sync-sdk wrapper, we assume DB logic here.
            # Ideally Yookassa SDK calls should be offloaded to threads or be async.
            
            return True
        return False
