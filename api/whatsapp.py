# api/whatsapp.py

import logging
from fastapi import APIRouter, Query, Request, Response, BackgroundTasks, HTTPException

from core.config import get_settings
from models.whatsapp import WebhookPayload
from utils.normalization import normalize_whatsapp_message
from utils.logging import log_message_data
from services.memory_store import memory_store
from services.openai_service import generate_reply
from services.whatsapp_service import send_whatsapp_message

# Initialize router and logger
router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()

# --- Webhook Verification Endpoint ---
@router.get("/webhook")
async def verify_webhook(
    mode: str = Query(..., alias="hub.mode"),
    token: str = Query(..., alias="hub.verify_token"),
    challenge: str = Query(..., alias="hub.challenge"),
):
    """
    Handles the webhook verification request from Meta.
    It checks the verify token and responds with the challenge.
    """
    if mode == "subscribe" and token == settings.VERIFY_TOKEN:
        logger.info("Webhook verified successfully.")
        return Response(content=challenge, media_type="text/plain")

    logger.warning(f"Webhook verification failed. Mode: {mode}, Token: {token}")
    raise HTTPException(status_code=403, detail="Webhook verification failed.")


# --- Task for Background Processing ---
async def process_and_reply(normalized_data: dict):
    """
    The main logic to process a message, get a reply, and send it back.
    This runs in the background to avoid webhook timeouts.
    """
    user_id = normalized_data["user_id"]
    user_text = normalized_data["text"]

    # 1. Generate a reply from the LLM agent
    reply_text = await generate_reply(user_id, user_text, memory_store)

    # 2. Send the reply back to the user via WhatsApp
    await send_whatsapp_message(to=user_id, text=reply_text)

    # 3. Log the interaction
    log_message_data(normalized_data, reply_text)

# --- Incoming Messages Endpoint ---
@router.post("/webhook")
async def receive_message(request: Request, background_tasks: BackgroundTasks):
    """
    Handles incoming messages and events from WhatsApp.
    It validates the payload, filters for user text messages, and
    schedules the processing to be done in the background.
    """
    try:
        payload_dict = await request.json()
        logger.info(f"Received webhook payload: {payload_dict}")

        # Use Pydantic to parse and validate the payload
        payload = WebhookPayload.parse_obj(payload_dict)

        for entry in payload.entry:
            for change in entry.changes:
                value = change.value

                # Filter out status updates and keep only actual user messages
                if value.messages:
                    normalized_data = normalize_whatsapp_message(value)
                    if normalized_data:
                        # Add the processing to background tasks
                        # This allows us to return a 200 OK to Meta immediately
                        background_tasks.add_task(process_and_reply, normalized_data)

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        # Still return 200 to prevent Meta from resending the webhook
        # but log the error for debugging.

    return Response(status_code=200)
