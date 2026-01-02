import httpx
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class MarzbanService:
    def __init__(self):
        self.base_url = os.getenv("MARZBAN_URL")
        self.username = os.getenv("MARZBAN_USERNAME")
        self.password = os.getenv("MARZBAN_PASSWORD")
        self.token = None
        # SSL verification - use env var for self-signed certs in dev
        verify_ssl = os.getenv("MARZBAN_VERIFY_SSL", "true").lower() != "false"
        self.client = httpx.AsyncClient(timeout=30.0, verify=verify_ssl)

    async def _authenticate(self):
        """Get JWT token from Marzban"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/admin/token",
                data={"username": self.username, "password": self.password},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            self.token = response.json().get("access_token")
            logger.info("Successfully authenticated with Marzban")
        except Exception as e:
            logger.error(f"Failed to authenticate with Marzban: {e}")
            raise

    async def _get_headers(self) -> Dict[str, str]:
        if not self.token:
            await self._authenticate()
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    async def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        try:
            headers = await self._get_headers()
            response = await self.client.get(f"{self.base_url}/api/user/{username}", headers=headers)
            
            if response.status_code == 404:
                return None
            
            if response.status_code == 401: # Token expired
                await self._authenticate()
                headers = await self._get_headers()
                response = await self.client.get(f"{self.base_url}/api/user/{username}", headers=headers)
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching user {username}: {e}")
            return None

    async def get_all_users(self) -> list:
        """Get all users from Marzban for admin panel."""
        try:
            headers = await self._get_headers()
            response = await self.client.get(f"{self.base_url}/api/users", headers=headers)
            if response.status_code == 200:
                data = response.json()
                return data.get("users", [])
            return []
        except Exception as e:
            logger.error(f"Error fetching all users: {e}")
            return []

    async def delete_user(self, username: str) -> bool:
        """Delete a user from Marzban."""
        try:
            headers = await self._get_headers()
            response = await self.client.delete(f"{self.base_url}/api/user/{username}", headers=headers)
            if response.status_code == 200:
                logger.info(f"Deleted user {username}")
                return True
            elif response.status_code == 404:
                logger.info(f"User {username} not found, nothing to delete")
                return True  # User doesn't exist, consider it success
            else:
                logger.error(f"Failed to delete user {username}: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error deleting user {username}: {e}")
            return False

    async def create_or_update_user(self, telegram_id: int, username: str = "User") -> Dict[str, Any]:
        """Create a user in Marzban, or return existing one if found."""
        marzban_username = f"user_{telegram_id}"
        
        # Check if exists
        existing_user = await self.get_user(marzban_username)
        if existing_user:
            logger.info(f"User {marzban_username} already exists in Marzban.")
            return existing_user

        headers = await self._get_headers()
        
        # 300 GB = 300 * 1024^3 bytes = 322122547200 bytes
        TRAFFIC_LIMIT_300GB = 300 * (1024 ** 3)
        
        # Default payload for new user
        # IMPORTANT: Marzban 0.8+ requires explicit 'inbounds' to bind proxies to inbound tags
        payload = {
            "username": marzban_username,
            "proxies": {
                "vless": {
                    "flow": ""  # Required for REALITY
                }
            },
            "inbounds": {
                "vless": ["VLESS_TCP_REALITY", "VLESS_WS_TLS"]  # Reality + WebSocket fallback
            },
            "expire": 0,  # Unlimited by default, managed by bot
            "data_limit": TRAFFIC_LIMIT_300GB,  # 300 GB limit
            "note": f"TG ID: {telegram_id} ({username})",
            "status": "active"
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/user",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            logger.info(f"Created new user {marzban_username} in Marzban.")
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error creating user: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"General error creating user: {e}")
            raise

    async def get_server_status(self) -> Dict[str, Any]:
        """Check Marzban server health status."""
        try:
            headers = await self._get_headers()
            response = await self.client.get(f"{self.base_url}/api/system", headers=headers)
            if response.status_code == 200:
                data = response.json()
                return {
                    "online": True,
                    "online_users": data.get("online_users", 0),
                    "cpu_usage": data.get("cpu_usage", 0),
                    "mem_usage": round(data.get("mem_used", 0) / data.get("mem_total", 1) * 100, 1) if data.get("mem_total") else 0
                }
        except Exception as e:
            logger.error(f"Error checking server status: {e}")
        
        return {"online": False, "online_users": 0, "cpu_usage": 0, "mem_usage": 0}

    async def get_subscription_info(self, telegram_id: int) -> Dict[str, Any]:
        """Get formatted subscription info for the bot"""
        user = await self.get_user(f"user_{telegram_id}")
        if not user:
            return None
        
        # Parse device info from User-Agent
        device_info = self._parse_user_agent(user.get("sub_last_user_agent", ""))
        
        # Get original subscription URL from Marzban
        original_sub_url = user.get("subscription_url", "")
        
        # TODO: Uncomment when API is deployed to public server
        # Rewrite URL to go through our proxy (for device tracking)
        # proxy_sub_url = original_sub_url
        # if original_sub_url:
        #     import re
        #     token_match = re.search(r'/sub/([a-zA-Z0-9_=-]+)$', original_sub_url)
        #     if token_match:
        #         token = token_match.group(1)
        #         our_api_host = os.getenv("API_HOST", "http://localhost:8000")
        #         proxy_sub_url = f"{our_api_host}/sub/{token}"
        
        return {
            "subscription_url": original_sub_url,  # Using Marzban URL directly for now
            "status": user.get("status", ""),
            "data_limit": user.get("data_limit", 0),
            "used_traffic": user.get("used_traffic", 0),
            "expire": user.get("expire", 0),
            "links": user.get("links", []),
            "last_device": device_info,
            "online_at": user.get("online_at", None)
        }
    
    def _parse_user_agent(self, ua: str) -> str:
        """Parse User-Agent string to extract device info."""
        if not ua:
            return None
        
        import re
        
        # Common patterns for VPN clients
        # Happ/1.5.2 (iOS 17.2; iPhone14,3)
        # V2RayTun/3.0 (Android 14; SM-S918B)
        # Shadowrocket/2.2.0 (iOS; iPhone)
        
        ua_lower = ua.lower()
        
        # Detect OS
        if "ios" in ua_lower or "iphone" in ua_lower or "ipad" in ua_lower:
            os_name = "iOS"
            # Try to extract version
            ios_match = re.search(r'ios[\s/]*([\d.]+)', ua_lower)
            if ios_match:
                os_name = f"iOS {ios_match.group(1)}"
            
            # Detect device type
            if "ipad" in ua_lower:
                device = "iPad"
            else:
                device = "iPhone"
            
            return f"{os_name} — {device}"
        
        elif "android" in ua_lower:
            os_name = "Android"
            android_match = re.search(r'android[\s/]*([\d.]+)', ua_lower)
            if android_match:
                os_name = f"Android {android_match.group(1)}"
            
            # Try to detect device model
            if "samsung" in ua_lower or "sm-" in ua_lower:
                device = "Samsung"
            elif "xiaomi" in ua_lower or "redmi" in ua_lower:
                device = "Xiaomi"
            elif "huawei" in ua_lower:
                device = "Huawei"
            else:
                device = "Android Device"
            
            return f"{os_name} — {device}"
        
        elif "windows" in ua_lower:
            return "Windows — PC"
        
        elif "mac" in ua_lower or "darwin" in ua_lower:
            return "macOS — Mac"
        
        elif "linux" in ua_lower:
            return "Linux — PC"
        
        # Generic fallback
        return ua[:30] + "..." if len(ua) > 30 else ua

# Singleton instance
marzban_service = MarzbanService()
