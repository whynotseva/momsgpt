"""
Marzban Admin Service - Admin operations for Marzban.
"""
from typing import Optional, Dict, Any, List
import httpx
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MarzbanAdminService:
    """Service for admin operations on Marzban."""
    
    _token: Optional[str] = None
    _base_url = os.getenv("MARZBAN_URL", "https://instabotwebhook.ru:8000")
    
    @classmethod
    async def _get_token(cls) -> str:
        """Get or refresh admin token."""
        if cls._token:
            return cls._token
            
        async with httpx.AsyncClient(verify=os.getenv("MARZBAN_VERIFY_SSL", "true").lower() != "false", timeout=30) as client:
            resp = await client.post(
                f"{cls._base_url}/api/admin/token",
                data={
                    "username": os.getenv("MARZBAN_USERNAME"),
                    "password": os.getenv("MARZBAN_PASSWORD")
                }
            )
            cls._token = resp.json().get("access_token")
            return cls._token
    
    @classmethod
    async def _get_headers(cls) -> Dict[str, str]:
        """Get auth headers."""
        token = await cls._get_token()
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    @classmethod
    async def get_all_users(cls) -> List[Dict[str, Any]]:
        """Get all users from Marzban."""
        try:
            headers = await cls._get_headers()
            async with httpx.AsyncClient(verify=os.getenv("MARZBAN_VERIFY_SSL", "true").lower() != "false", timeout=30) as client:
                resp = await client.get(f"{cls._base_url}/api/users", headers=headers)
                data = resp.json()
                return data.get("users", [])
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return []
    
    @classmethod
    async def get_system_status(cls) -> Dict[str, Any]:
        """Get Marzban system status."""
        try:
            headers = await cls._get_headers()
            async with httpx.AsyncClient(verify=os.getenv("MARZBAN_VERIFY_SSL", "true").lower() != "false", timeout=30) as client:
                resp = await client.get(f"{cls._base_url}/api/system", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "online": True,
                        "version": data.get("version", "Unknown"),
                        "online_users": data.get("users_active", 0),
                        "total_users": data.get("total_user", 0),
                        "cpu_usage": round(data.get("cpu_usage", 0), 1),
                        "mem_used": data.get("mem_used", 0),
                        "mem_total": data.get("mem_total", 0),
                        "uptime": data.get("uptime", 0)
                    }
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
        
        return {"online": False}
    
    @classmethod
    async def disable_user(cls, username: str) -> bool:
        """Disable a user."""
        try:
            headers = await cls._get_headers()
            async with httpx.AsyncClient(verify=os.getenv("MARZBAN_VERIFY_SSL", "true").lower() != "false", timeout=30) as client:
                resp = await client.put(
                    f"{cls._base_url}/api/user/{username}",
                    headers=headers,
                    json={"status": "disabled"}
                )
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"Error disabling user: {e}")
            return False
    
    @classmethod
    async def enable_user(cls, username: str) -> bool:
        """Enable a user."""
        try:
            headers = await cls._get_headers()
            async with httpx.AsyncClient(verify=os.getenv("MARZBAN_VERIFY_SSL", "true").lower() != "false", timeout=30) as client:
                resp = await client.put(
                    f"{cls._base_url}/api/user/{username}",
                    headers=headers,
                    json={"status": "active"}
                )
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"Error enabling user: {e}")
            return False
    
    @classmethod
    async def reset_user_traffic(cls, username: str) -> bool:
        """Reset user's traffic usage."""
        try:
            headers = await cls._get_headers()
            async with httpx.AsyncClient(verify=os.getenv("MARZBAN_VERIFY_SSL", "true").lower() != "false", timeout=30) as client:
                resp = await client.post(
                    f"{cls._base_url}/api/user/{username}/reset",
                    headers=headers
                )
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"Error resetting traffic: {e}")
            return False
    
    @classmethod
    async def extend_user(cls, username: str, days: int) -> bool:
        """Extend user's subscription."""
        try:
            headers = await cls._get_headers()
            # Get current expiry
            async with httpx.AsyncClient(verify=os.getenv("MARZBAN_VERIFY_SSL", "true").lower() != "false", timeout=30) as client:
                user_resp = await client.get(f"{cls._base_url}/api/user/{username}", headers=headers)
                user = user_resp.json()
                
                current_expire = user.get("expire", 0)
                if current_expire == 0:
                    # No expiry set, set from now
                    new_expire = int((datetime.now() + timedelta(days=days)).timestamp())
                else:
                    # Extend from current expiry
                    new_expire = current_expire + (days * 86400)
                
                resp = await client.put(
                    f"{cls._base_url}/api/user/{username}",
                    headers=headers,
                    json={"expire": new_expire}
                )
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"Error extending user: {e}")
            return False
