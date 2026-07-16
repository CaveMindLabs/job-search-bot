"""
api/whatsapp.py
Handles incoming Meta webhooks, background tasks, and message sending.
"""
import logging
from typing import Annotated
from fastapi import APIRouter, Query, Request, Response, BackgroundTasks, HTTPException, Depends, Header

from core.config import get_settings
from api.dependencies import get_api_key
from models.whatsapp import WebhookPayload, OutboundMessagePayload
from utils.normalization import normalize_whatsapp_message
from services.memory_store import memory_store
from services.whatsapp_service import send_whatsapp_message
from api.message_processor import process_and_reply, list_available_models


async def list_available_models():
    return ["gemini-1.5-flash", "gemini-1.5-flash-lite"]


router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()

async def verify_api_key(x_api_key: Annotated[str, Header()]):
    if x_api_key != settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")


@router.get("/models", response_model=list[str], dependencies=[Depends(verify_api_key)])
async def get_available_models():
    return await list_available_models()

@router.get("/webhook")
async def verify_webhook(mode: str = Query(..., alias="hub.mode"), token: str = Query(..., alias="hub.verify_token"), challenge: str = Query(..., alias="hub.challenge")):
    if mode == "subscribe" and token == settings.VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Webhook verification failed.")


@router.post("/webhook")
async def receive_message(request: Request, background_tasks: BackgroundTasks):
    try:
        payload_dict = await request.json()
        payload = WebhookPayload.parse_obj(payload_dict)
        for entry in payload.entry:
            for change in entry.changes:
                value = change.value
                if value.messages:
                    normalized_data = normalize_whatsapp_message(value)
                    if normalized_data:
                        background_tasks.add_task(process_and_reply, normalized_data)
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
    return Response(status_code=200)

@router.post("/send", summary="Send an outbound message", dependencies=[Depends(get_api_key)])
async def send_from_internal(payload: OutboundMessagePayload):
    try:
        await send_whatsapp_message(to=payload.to, text=payload.text)
        return {"status": "success", "message": f"Message queued to be sent to {payload.to}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")