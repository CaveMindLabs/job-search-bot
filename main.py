"""
main.py
FastAPI application entry point.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from api.whatsapp import router as whatsapp_router
from utils.logging import IN_MEMORY_LOGS 
from core.config import get_settings
# Modular Agent Imports
from agents.pipeline_generate import run_job_search_pipeline
from agents.utility_agents import run_close_the_loop

app_configs = {
    "title": "WhatsApp Job Search Agent",
    "description": "A chatbot agent for WhatsApp using FastAPI and CrewAI.",
    "version": "0.1.0",
}

if get_settings().ENVIRONMENT != "production":
    app_configs["docs_url"] = "/docs"
    app_configs["redoc_url"] = "/redoc"
    app_configs["openapi_url"] = "/openapi.json"
else:
    app_configs["docs_url"] = None
    app_configs["redoc_url"] = None
    app_configs["openapi_url"] = None

app = FastAPI(**app_configs)
app.include_router(whatsapp_router, prefix="/whatsapp", tags=["WhatsApp"])

class JobRequest(BaseModel):
    job_input: str
    company_name: str

@app.post("/generate-cv", tags=["CV Generation"])
def generate_cv(request: JobRequest):
    if not request.job_input.strip() or not request.company_name.strip():
        raise HTTPException(status_code=400, detail="Fields cannot be empty.")
    try:
        result = run_job_search_pipeline(request.job_input, request.company_name)
        return {"status": "success", "message": f"CV Pipeline triggered for {request.company_name}.", "agent_output": str(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

class FeedbackRequest(BaseModel):
    company_name: str
    outcome: str
    good_feedback: str
    bad_feedback: str

@app.post("/feedback", tags=["Feedback Loop"])
def close_the_loop_endpoint(request: FeedbackRequest):
    if not request.company_name.strip():
        raise HTTPException(status_code=400, detail="Company name is required.")
    try:
        new_rule = run_close_the_loop(request.company_name, request.outcome, request.good_feedback, request.bad_feedback)
        return {"status": "success", "message": "Rule saved to database.", "extracted_rule": new_rule}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.get("/", tags=["Health Check"])
async def root():
    return {"status": "ok", "message": "Welcome to the WhatsApp Job Search Agent!"}

@app.get("/logs", tags=["Debugging"])
async def get_logs():
    return {"logs": IN_MEMORY_LOGS[-100:]}