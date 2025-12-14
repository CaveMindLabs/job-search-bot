# services/whatsapp_service.py

import httpx
import logging
from core.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)

# Initialize settings
settings = get_settings()

# Dynamically build the API URL from settings
WHATSAPP_API_URL = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{settings.PHONE_NUMBER_ID}/messages"

async def send_whatsapp_message(to: str, text: str) -> None:
    """
    Sends a text message to a WhatsApp user via the Cloud API.
    """
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }

    try:
        async with httpx.AsyncClient() as client:
            logger.info(f"Sending message to {to}")
            response = await client.post(WHATSAPP_API_URL, json=payload, headers=headers)
            response.raise_for_status()  # Raises an exception for 4xx or 5xx status codes
            logger.info(f"Message sent successfully to {to}. Response: {response.json()}")

    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to send message to {to}. Status: {e.response.status_code}, Response: {e.response.text}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending message to {to}: {e}")
