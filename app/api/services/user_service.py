from app.api.models import User
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.schemas import UserCreate
from app.api.services.xray import marzban_service
import logging

logger = logging.getLogger(__name__)

class UserService:
    async def create_user(self, session: AsyncSession, user: UserCreate):
        # 1. Create or get user in DB
        result = await session.execute(select(User).where(User.telegram_id == user.telegram_id))
        db_user = result.scalars().first()
        
        if not db_user:
            db_user = User(
                telegram_id=user.telegram_id,
                username=user.username,
                full_name=user.full_name
            )
            session.add(db_user)
            await session.commit()
            await session.refresh(db_user)
        
        # 2. Create/Sync user in Marzban (Critical Step)
        try:
            # We pass username for descriptive note in Marzban
            username_safe = user.username or "NoUsername"
            await marzban_service.create_or_update_user(
                telegram_id=user.telegram_id,
                username=username_safe
            )
            logger.info(f"Synced user {user.telegram_id} with Marzban")
        except Exception as e:
            logger.error(f"Failed to sync with Marzban: {e}")
            # We continue even if Marzban fails
            
        return db_user

    async def get_user(self, session: AsyncSession, telegram_id: int):
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalars().first()
        return user

    async def get_user_subscription(self, session: AsyncSession, telegram_id: int):
        """Get real subscription info from Marzban"""
        # We fetch directly from Marzban to get the freshest stats (traffic)
        marzban_info = await marzban_service.get_subscription_info(telegram_id)
        
        if not marzban_info:
            # If not in Marzban, try creating it?
            try:
                await marzban_service.create_or_update_user(telegram_id)
                marzban_info = await marzban_service.get_subscription_info(telegram_id)
            except Exception as e:
                logger.error(f"Could not create missing Marzban user: {e}")
                return None
            
        return marzban_info
