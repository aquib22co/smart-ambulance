import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

async def send_whatsapp_message(to_number: str, text: str) -> bool:
    """
    Sends a text message using the WhatsApp Cloud API.
    """
    if not settings.WHATSAPP_PHONE_NUMBER_ID or not settings.WHATSAPP_ACCESS_TOKEN:
        logger.error("WhatsApp configuration is missing in environment variables.")
        return False
        
    url = f"https://graph.facebook.com/v19.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {
            "body": text
        }
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=10.0)
            
            if response.status_code in [200, 201]:
                logger.info(f"Message sent successfully to {to_number}")
                return True
            else:
                logger.error(f"Failed to send message: {response.text}")
                return False
    except Exception as e:
        logger.error(f"Error communicating with WhatsApp API: {e}")
        return False
