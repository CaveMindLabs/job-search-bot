# main.py

from fastapi import FastAPI
from api.whatsapp import router as whatsapp_router
from utils.logging import IN_MEMORY_LOGS # For a potential debug endpoint

# Initialize FastAPI app
app = FastAPI(
    title="WhatsApp FastAPI Agent",
    description="A chatbot agent for WhatsApp using FastAPI and OpenAI.",
    version="0.1.0",
)

# Include the WhatsApp webhook router
app.include_router(whatsapp_router, prefix="/whatsapp", tags=["WhatsApp"])

@app.get("/", tags=["Health Check"])
async def root():
    """
    A simple health check endpoint.
    """
    return {"status": "ok", "message": "Welcome to the WhatsApp Agent!"}

@app.get("/logs", tags=["Debugging"])
async def get_logs():
    """
    An endpoint to view the last 100 in-memory logs (for debugging).
    """
    return {"logs": IN_MEMORY_LOGS[-100:]}
