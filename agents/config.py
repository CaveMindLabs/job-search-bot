"""
agents/config.py
Centralizes LLM and Tool initializations for CrewAI agents.
"""
import os
from dotenv import load_dotenv
from crewai import LLM
from crewai_tools import ScrapeWebsiteTool, SerperDevTool

load_dotenv()

# Primary Fast LLM (Administrative Tasks)
gemini_flash = LLM(
    model='gemini/gemini-3.5-flash', 
    api_key=os.environ.get("GEMINI_API_KEY")
)

# Deep Reasoning LLM (Strategic Tasks)
gemini_pro = LLM(
    model='gemini/gemini-3.1-pro-preview', 
    api_key=os.environ.get("GEMINI_API_KEY")
)

# Active Tools
scrape_tool = ScrapeWebsiteTool()
search_tool = SerperDevTool(n_results=4, search_params={"tbs": "qdr:m"})