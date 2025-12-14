# models/whatsapp.py

from pydantic import BaseModel, Field
from typing import List, Optional

# Models for the incoming webhook payload from Meta
# Based on: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/components

class Message(BaseModel):
    id: str
    from_number: str = Field(..., alias='from') # Use an alias for the 'from' keyword
    timestamp: str
    text: Optional[dict] = None
    type: str

class Contact(BaseModel):
    wa_id: str
    profile: dict

class Metadata(BaseModel):
    display_phone_number: str
    phone_number_id: str

class Value(BaseModel):
    messaging_product: str
    metadata: Metadata
    contacts: Optional[List[Contact]] = None
    messages: Optional[List[Message]] = None
    statuses: Optional[List[dict]] = None # To catch status updates

class Change(BaseModel):
    value: Value
    field: str

class Entry(BaseModel):
    id: str
    changes: List[Change]

class WebhookPayload(BaseModel):
    object: str
    entry: List[Entry]
