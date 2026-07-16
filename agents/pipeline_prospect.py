import os
import json
import requests
import chromadb
from urllib.parse import urlparse
from crewai import Task, Crew

# Import only the agents this specific pipeline needs
from agents.agent_definitions import prospector_agent
from utils.api_utils import run_crew_with_backoff
from api.cache_manager import update_user_cache
from utils.url_validator import validate_and_filter_urls

def run_job_prospector(search_query, user_id):
    """Searches the web natively and formats the output via CrewAI."""
    print(f"Searching for jobs natively: {search_query}")
    
    # 1. Read the static qualifications & guidelines files
    qual_path = os.path.join(os.getcwd(), "C-core", "qualifications.md")
    guide_path = os.path.join(os.getcwd(), "C-core", "guidelines.md")
    
    try:
        with open(qual_path, "r", encoding="utf-8") as f: 
            qualifications = f.read()
        with open(guide_path, "r", encoding="utf-8") as f: 
            guidelines = f.read()
    except FileNotFoundError:
        qualifications, guidelines = "Qualifications file missing.", "Guidelines file missing."

    # 2. Pull dynamic memory (Feedback Rules) from ChromaDB
    try:
        db_path = os.path.join(os.getcwd(), "chroma_db")
        chroma_client = chromadb.PersistentClient(path=db_path)
        rules_collection = chroma_client.get_or_create_collection(name="career_rules")
        rules_data = rules_collection.get()
        historical_rules = "\n- ".join(rules_data['documents']) if rules_data and rules_data.get('documents') else "No previous rules."
    except Exception:
        historical_rules = "No previous rules."

    # 3. NATIVE PYTHON SEARCH (Bypassing the ReAct Loop)
    serper_api_key = os.environ.get("SERPER_API_KEY")
    search_url = "https://google.serper.dev/search"
    payload = json.dumps({
      "q": f"{search_query}",
      "tbs": "qdr:w", # Restricts search results strictly to the past 7 days
      "num": 5
    })
    headers = {
      'X-API-KEY': serper_api_key,
      'Content-Type': 'application/json'
    }
    
    try:
        response = requests.request("POST", search_url, headers=headers, data=payload, timeout=10)
        search_results = response.json().get("organic", [])
        
        if not search_results:
            return "⚠️ No active jobs found for that query in the past 7 days."
            
        raw_job_data = ""
        found_sources = set()
        
        for job in search_results:
            link = job.get('link', '')
            raw_job_data += f"Title: {job.get('title')}\nLink: {link}\nSnippet: {job.get('snippet')}\n\n"
            
            # Safely parse the platform domain name for the sources list
            if link:
                domain = urlparse(link).netloc
                # Turn 'job-boards.greenhouse.io' into 'Greenhouse'
                clean_source = domain.replace("www.", "").split('.')[0].capitalize()
                found_sources.add(clean_source)
                
        sources_list_str = ", ".join(found_sources)
    except Exception as e:
        return f"⚠️ Search API Failed: {str(e)}"

    # 4. SINGLE-CALL LLM FORMATTING
    search_task = Task(
        description=f"""
        The user is looking for jobs based on this request: "{search_query}".
        
        Here are the VERIFIED, raw search results from the search engine:
        {raw_job_data}
        
        Here are the primary hosting platforms identified for these links:
        {sources_list_str}
        
        Here are the user's core qualifications:
        {qualifications}
        
        Here are the strict search guidelines you MUST follow:
        {guidelines}
        
        Here are past feedback rules from the user you MUST apply:
        {historical_rules}
        
        Instructions:
        1. Read the raw job search results provided above. Ignore results that completely violate the guidelines.
        2. Format the output as a clean, easy-to-read WhatsApp message containing the Job Title, Company, Location, and the exact URL provided in the raw data text.
        3. Include a 'Search Sources' section at the bottom of your message listing the platform names provided ({sources_list_str}).
        4. CRITICAL: You are strictly forbidden from inventing, guessing, or altering URLs. Only use the links exactly as they are written in the raw data text.
        """,
        expected_output="A clean WhatsApp formatted string containing job details and a Search Sources section.",
        agent=prospector_agent
    )

    crew = Crew(agents=[prospector_agent], tasks=[search_task], verbose=False)
    
    try:
        result = run_crew_with_backoff(crew)
        result = validate_and_filter_urls(result)
        update_user_cache(user_id, {
            "last_search_query": search_query,
            "last_found_jobs": result 
        })
        return result
    except Exception:
        raise Exception("⚠️ Pipeline aborted: The Prospector Agent encountered continuous server limits (Error 503).")