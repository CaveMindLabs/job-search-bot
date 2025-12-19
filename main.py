# main.py

from fastapi import FastAPI
from api.whatsapp import router as whatsapp_router
from utils.logging import IN_MEMORY_LOGS # For a potential debug endpoint
from core.config import get_settings

# Define app arguments in a dictionary
app_configs = {
    "title": "WhatsApp FastAPI Agent",
    "description": "A chatbot agent for WhatsApp using FastAPI and OpenAI.",
    "version": "0.1.0",
}
# Conditionally add the doc URLs if not in production
if get_settings().ENVIRONMENT != "production":
    app_configs["docs_url"] = "/docs"
    app_configs["redoc_url"] = "/redoc"
    app_configs["openapi_url"] = "/openapi.json"
else:
    app_configs["docs_url"] = None
    app_configs["redoc_url"] = None
    app_configs["openapi_url"] = None

# Initialize FastAPI app
app = FastAPI(**app_configs)

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
