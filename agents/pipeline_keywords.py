from agents.agent_definitions import extractor_agent, keyword_agent
from agents.config import gemini_pro
from api.cache_manager import update_user_cache
from crewai import Task, Crew
from utils.api_utils import run_crew_with_backoff

def run_keyword_extraction_only(url, user_id):
    """Extracts JD data and keywords, then caches them without generating a CV."""
    
    # 1. Extract Job Data
    extract_task = Task(
        description=f"Scrape {url}. Return a JSON with 'Description', 'Requirements', 'Responsibilities'.",
        expected_output="Valid JSON string.",
        agent=extractor_agent
    )
    extract_crew = Crew(agents=[extractor_agent], tasks=[extract_task], verbose=False, max_rpm=10)
    
    try:
        job_data = run_crew_with_backoff(extract_crew)
    except Exception:
        return "❌ Failed to extract JD data for keyword analysis."

    # 2. Extract Keywords
    keyword_task = Task(
        description=f"Analyze: {job_data}. Extract 10-15 critical technical keywords. Return ONLY a comma-separated list.",
        expected_output="Comma-separated string.",
        agent=keyword_agent
    )
    keyword_crew = Crew(agents=[keyword_agent], tasks=[keyword_task], verbose=False, max_rpm=10)
    
    try:
        keyword_list = run_crew_with_backoff(keyword_crew)
    except Exception:
        return "❌ Failed to extract keywords."

    # 3. Update Cache
    update_user_cache(user_id, {
        "last_jd_url": url,
        "last_jd_keywords": keyword_list,
        "last_jd_data": job_data
    })
    
    return f"✅ Keywords extracted and cached for {url}:\n\n{keyword_list}"