"""
Subscription Proxy Router.
Intercepts subscription requests from VPN clients (Happ), 
logs device info, and proxies to Marzban.
"""
from fastapi import APIRouter, Request, Response
from fastapi.responses import PlainTextResponse
import httpx
import logging
import re
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sub", tags=["subscription"])

MARZBAN_URL = os.getenv("MARZBAN_URL", "https://instabotwebhook.ru:8000")


def parse_device_from_headers(headers: dict) -> dict:
    """Parse device info from HTTP headers."""
    user_agent = headers.get("user-agent", "")
    
    device_info = {
        "user_agent": user_agent,
        "device_name": None,
        "os_version": None,
        "app_name": None,
        "app_version": None
    }
    
    if not user_agent:
        return device_info
    
    ua_lower = user_agent.lower()
    
    # Parse Happ: "Happ/3.7.0/ios CFNetwork/3860.300.31 Darwin/25.2.0"
    # Or other clients
    
    # Extract app name and version
    app_match = re.match(r'^(\w+)/([0-9.]+)', user_agent)
    if app_match:
        device_info["app_name"] = app_match.group(1)
        device_info["app_version"] = app_match.group(2)
    
    # Darwin version to iOS version mapping (approximate)
    darwin_to_ios = {
        "25.": "18.",  # iOS 18.x
        "24.": "17.",  # iOS 17.x
        "23.": "16.",  # iOS 16.x
        "22.": "15.",  # iOS 15.x
        "21.": "14.",  # iOS 14.x
    }
    
    darwin_match = re.search(r'darwin/(\d+)\.(\d+)', ua_lower)
    if darwin_match:
        major = darwin_match.group(1)
        minor = darwin_match.group(2)
        for darwin_prefix, ios_prefix in darwin_to_ios.items():
            if major + "." == darwin_prefix:
                # Convert Darwin minor to approximate iOS minor
                ios_minor = int(minor) // 100 if int(minor) > 10 else minor
                device_info["os_version"] = f"iOS {ios_prefix}{ios_minor}"
                break
    
    # Detect device type
    if "iphone" in ua_lower or "/ios" in ua_lower:
        device_info["device_name"] = "iPhone"
    elif "ipad" in ua_lower:
        device_info["device_name"] = "iPad"
    elif "android" in ua_lower:
        device_info["device_name"] = "Android"
        # Try to extract Android version
        android_match = re.search(r'android[/\s]*([\d.]+)', ua_lower)
        if android_match:
            device_info["os_version"] = f"Android {android_match.group(1)}"
    elif "windows" in ua_lower:
        device_info["device_name"] = "Windows PC"
        device_info["os_version"] = "Windows"
    elif "mac" in ua_lower:
        device_info["device_name"] = "Mac"
        device_info["os_version"] = "macOS"
    
    # Log full headers for debugging
    logger.info(f"Device parsed: {device_info}")
    
    return device_info


@router.get("/{token}")
async def subscription_proxy(token: str, request: Request):
    """
    Proxy subscription requests to Marzban while capturing device info.
    """
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    # Parse device info from headers
    headers_dict = dict(request.headers)
    device_info = parse_device_from_headers(headers_dict)
    
    # Log for debugging
    logger.info(f"Subscription request for token: {token[:20]}...")
    logger.info(f"Client IP: {client_ip}")
    logger.info(f"User-Agent: {device_info['user_agent']}")
    logger.info(f"Parsed device: {device_info['device_name']} / {device_info['os_version']}")
    
    # TODO: Save device info to database (link token to user)
    # This requires decoding the token to get username
    
    # Proxy request to Marzban
    try:
        async with httpx.AsyncClient(verify=os.getenv("MARZBAN_VERIFY_SSL", "true").lower() != "false", timeout=30) as client:
            marzban_url = f"{MARZBAN_URL}/sub/{token}"
            response = await client.get(marzban_url, headers={
                "User-Agent": headers_dict.get("user-agent", "")
            })
            
            return PlainTextResponse(
                content=response.text,
                status_code=response.status_code,
                headers={
                    "Content-Type": response.headers.get("Content-Type", "text/plain")
                }
            )
    except Exception as e:
        logger.error(f"Error proxying to Marzban: {e}")
        return PlainTextResponse(content="Error", status_code=500)
