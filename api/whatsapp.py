# api/whatsapp.py

import logging
import re
from fastapi import APIRouter, Query, Request, Response, BackgroundTasks, HTTPException, Depends, Header
from typing import Annotated

from core.config import get_settings
from api.dependencies import get_api_key
from models.whatsapp import WebhookPayload, OutboundMessagePayload
from utils.normalization import normalize_whatsapp_message
from utils.logging import log_message_data
from services.memory_store import memory_store
from services.openai_service import generate_reply, list_available_models
from services.whatsapp_service import send_whatsapp_message

# Initialize router and logger
router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()

# --- Security Dependency ---
async def verify_api_key(x_api_key: Annotated[str, Header()]):
    """
    Dependency to verify the internal API key.
    """
    if x_api_key != settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

# --- HELPER FUNCTION ---
async def format_and_send_model_list(user_id: str):
    """
    Fetches, formats, and sends the list of available models to the user.
    """
    models = await list_available_models()
    if models:
        # Sort models, maybe putting 'gpt-4o' variants at the top for prominence
        models.sort(key=lambda x: ('gpt-4o' not in x, 'mini' in x, x))
        formatted_list = "\n- ".join(models)
        reply_text = (
            "To select one, send a message like this:\n"
            '`/Use model: "gpt-4o-mini"`\n\n'
            "You can choose from these available models:\n\n"
            f"- {formatted_list}\n\n"
            "To select one, send a message like this:\n"
            '`/Use model: "gpt-4o-mini"`\n\n'
        )
        await send_whatsapp_message(to=user_id, text=reply_text)

# --- Get Available Models ---
@router.get(
    "/models", 
    response_model=list[str],
    dependencies=[Depends(verify_api_key)]
)
async def get_available_models():
    """
    Returns a list of available OpenAI chat models.
    This endpoint is secured by the internal API key.
    """
    return await list_available_models()

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
    Processes a message, handling commands for model selection and generating replies.
    The logic for listing models is now handled by the LLM via tool calling.
    """
    user_id = normalized_data["user_id"]
    user_text = normalized_data["text"].strip()

    # --- Command Router ---

    # 1. Check for the model selection command: /Use model: "..."
    # Accepts both single and double quotes
    model_selection_match = re.match(r'/Use model: [\'"]([^\'"]+)[\'"]', user_text, re.IGNORECASE)
    if model_selection_match:
        model_name = model_selection_match.group(1)
        # Optional: Validate if the model exists
        available_models = await list_available_models()
        if model_name in available_models:
            memory_store.add_message(user_id, "user", user_text)
            memory_store.set_user_preference(user_id, 'model', model_name)
            reply_text = f"✅ Model for this chat is now set to `{model_name}`."
            await send_whatsapp_message(to=user_id, text=reply_text)
            log_message_data(normalized_data, reply_text)
        else:
            error_text = f"❌ Sorry, the model `{model_name}` is not available."
            await send_whatsapp_message(to=user_id, text=error_text)
            # Proactively send the list of correct models
            await format_and_send_model_list(user_id)
            # We don't need to log the list sending, just the primary interaction
            log_message_data(normalized_data, error_text + " [Sent model list]")
        return # Stop processing after handling the command

    # 2. For all other messages, call the agent and let it handle tool use
    # We pass `send_whatsapp_message` as the callback.
    final_reply_text = await generate_reply(
        user_id=user_id,
        user_text=user_text,
        send_message_callback=send_whatsapp_message
    )

    # Send the final LLM-generated reply
    if final_reply_text:
        await send_whatsapp_message(to=user_id, text=final_reply_text)

    log_message_data(normalized_data, final_reply_text or "[No final reply text]")

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

# --- NEW ENDPOINT FOR N8N ---

@router.post(
    "/send",
    summary="Send an outbound message",
    description="Endpoint for internal services like n8n to send a WhatsApp message.",
    dependencies=[Depends(get_api_key)] # This applies the security check!
)
async def send_from_internal(payload: OutboundMessagePayload):
    """
    Receives a recipient 'to' and 'text' and sends a WhatsApp message.
    This endpoint is protected by an API key.
    """
    logger.info(f"Received request to send message to {payload.to} from internal service.")
    try:
        await send_whatsapp_message(to=payload.to, text=payload.text)
        return {"status": "success", "message": f"Message queued to be sent to {payload.to}."}
    except Exception as e:
        logger.error(f"Failed to send message from internal endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while trying to send the message: {e}"
        )
