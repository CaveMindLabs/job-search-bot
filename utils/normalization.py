# utils/normalization.py

from datetime import datetime, timezone
from models.whatsapp import Value

def normalize_whatsapp_message(value: Value) -> dict | None:
    """
    Extracts key information from the WhatsApp message payload
    and returns it in a clean, standardized dictionary format.
    """
    if not value.messages:
        return None # Not a user message

    message = value.messages[0]

    # We only handle text messages for now
    if message.type != "text":
        return None

    contact = value.contacts[0] if value.contacts else None

    # Convert Unix timestamp string to a readable ISO 8601 format string
    ts_iso = datetime.fromtimestamp(
        int(message.timestamp), tz=timezone.utc
    ).isoformat()

    return {
        "user_id": message.from_number,
        "user_name": contact.profile.get("name", "Unknown") if contact else "Unknown",
        "text": message.text.get("body", ""),
        "message_id": message.id,
        "timestamp_unix": int(message.timestamp),
        "timestamp_iso": ts_iso,
        "waba_phone_number_id": value.metadata.phone_number_id,
        "business_display_number": value.metadata.display_phone_number,
        "raw": value.dict() # Include the original event as a dict
    }
