"""
Stats Service - Statistics aggregation for admin dashboard.
"""
from typing import Optional, Dict, Any, List
from sqlalchemy import select, func
from datetime import datetime, timedelta

from app.api.services.xray import marzban_service


class StatsService:
    """Service for aggregating admin statistics."""
    
    @staticmethod
    async def get_overview() -> Dict[str, Any]:
        """Get dashboard overview statistics."""
        try:
            # Get all users from Marzban
            users = await marzban_service.get_all_users()
            
            total_users = len(users) if users else 0
            active_users = sum(1 for u in users if u.get("status") == "active") if users else 0
            
            # Calculate total traffic
            total_traffic = sum(u.get("used_traffic", 0) for u in users) if users else 0
            total_traffic_gb = round(total_traffic / (1024**3), 2)
            
            # Get server status
            server = await marzban_service.get_server_status()
            
            return {
                "total_users": total_users,
                "active_users": active_users,
                "total_traffic_gb": total_traffic_gb,
                "online_users": server.get("online_users", 0) if server.get("online") else 0,
                "server_online": server.get("online", False)
            }
        except Exception as e:
            return {
                "total_users": 0,
                "active_users": 0,
                "total_traffic_gb": 0,
                "online_users": 0,
                "server_online": False,
                "error": str(e)
            }
    
    @staticmethod
    async def get_users(search: Optional[str] = None, status: Optional[str] = None, page: int = 1) -> Dict[str, Any]:
        """Get paginated list of users."""
        try:
            users = await marzban_service.get_all_users()
            if not users:
                return {"items": [], "total": 0}
            
            # Filter by search
            if search:
                users = [u for u in users if search.lower() in u.get("username", "").lower()]
            
            # Filter by status
            if status:
                users = [u for u in users if u.get("status") == status]
            
            # Pagination
            per_page = 20
            start = (page - 1) * per_page
            end = start + per_page
            
            return {
                "items": users[start:end],
                "total": len(users)
            }
        except Exception:
            return {"items": [], "total": 0}
    
    @staticmethod
    async def get_user_detail(telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed user information."""
        try:
            username = f"user_{telegram_id}"
            return await marzban_service.get_user(username)
        except Exception:
            return None
    
    @staticmethod
    async def get_payments(status: Optional[str] = None, page: int = 1) -> Dict[str, Any]:
        """Get paginated payment history."""
        # TODO: Implement when payment system is ready
        return {"items": [], "total": 0}
    
    @staticmethod
    async def get_revenue_stats() -> Dict[str, Any]:
        """Get revenue statistics."""
        # TODO: Implement when payment system is ready
        return {
            "today": 0,
            "week": 0,
            "month": 0,
            "total": 0
        }
