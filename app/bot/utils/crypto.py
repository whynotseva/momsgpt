"""
Crypto utilities for encrypting VPN links via Happ's official API.
Uses https://crypto.happ.su/api.php to encrypt vless:// links into happ://crypt4/ format.
"""
import aiohttp
import logging

logger = logging.getLogger(__name__)

HAPP_CRYPTO_API = "https://crypto.happ.su/api.php"

async def encrypt_vless_link(vless_url: str, name: str = "🤎MomsVPN") -> str:
    """
    Encrypt a subscription URL using Happ's official crypto API.
    
    Output: happ://crypt4/...
    
    If encryption fails, returns the original link.
    """
    try:
        async with aiohttp.ClientSession() as session:
            # Use original URL format (custom name investigation in progress)
            payload = {"url": vless_url}
            async with session.post(HAPP_CRYPTO_API, json=payload, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    encrypted = data.get("encrypted_link")
                    if encrypted:
                        logger.info("Successfully encrypted link via Happ API")
                        return encrypted
                    else:
                        logger.warning(f"Happ API returned no encrypted_link: {data}")
                else:
                    logger.warning(f"Happ API returned status {resp.status}")
    except Exception as e:
        logger.error(f"Failed to encrypt via Happ API: {e}")
    
    # Fallback to original link if encryption fails
    return vless_url


# For testing
if __name__ == "__main__":
    import asyncio
    
    async def test():
        test_url = "vless://test-uuid@1.1.1.1:443?security=reality&sni=google.com"
        result = await encrypt_vless_link(test_url)
        print(f"Encrypted: {result[:80]}...")
    
    asyncio.run(test())
