"""
API Client for Bot-to-Backend communication.
Uses Marzban service directly for production deployment.
"""
import logging

logger = logging.getLogger(__name__)


class APIClient:
    """API Client that uses Marzban service directly."""
    
    def __init__(self):
        pass

    async def close(self):
        """No session to close in direct mode."""
        pass

    async def create_user(self, telegram_id: int, username: str, full_name: str):
        """Create user via Marzban directly."""
        try:
            from app.api.services.xray import marzban_service
            return await marzban_service.create_or_update_user(telegram_id, username)
        except Exception as e:
            logger.error(f"create_user error: {e}")
            return None

    async def get_user(self, telegram_id: int):
        """Get user from Marzban directly."""
        try:
            from app.api.services.xray import marzban_service
            username = f"user_{telegram_id}"
            return await marzban_service.get_user(username)
        except Exception as e:
            logger.error(f"get_user error: {e}")
            return None

    async def get_subscription(self, telegram_id: int):
        """Get subscription data from Marzban directly."""
        try:
            from app.api.services.xray import marzban_service
            username = f"user_{telegram_id}"
            user = await marzban_service.get_user(username)
            if user:
                return {
                    "subscription_url": user.get("subscription_url"),
                    "traffic_used": user.get("used_traffic", 0),
                    "traffic_limit": user.get("data_limit", 0),
                    "expire": user.get("expire"),
                    "status": user.get("status")
                }
            return None
        except Exception as e:
            logger.error(f"get_subscription error: {e}")
            return None

    async def create_payment(self, telegram_id: int, amount: float, description: str):
        """Create payment - placeholder for YooKassa integration."""
        logger.warning("Payment system not integrated yet")
        return None

    async def get_server_status(self):
        """Get server status from Marzban directly."""
        try:
            from app.api.services.xray import marzban_service
            return await marzban_service.get_server_status()
        except Exception as e:
            logger.error(f"get_server_status error: {e}")
            return {"online": False}


# Singleton instance
api = APIClient()
