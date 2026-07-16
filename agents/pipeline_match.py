import os
from crewai import Task, Crew
# Import only the agents this specific pipeline needs
from agents.agent_definitions import prospector_agent, extractor_agent, router_agent, reviewer_agent
from agents.config import gemini_pro, gemini_flash
from api.cache_manager import update_user_cache, get_user_cache 
from utils.api_utils import run_crew_with_backoff


def run_best_cv_match_pipeline(url, user_id):
    """Finds the best existing CV for a given job URL by indexing the correct subfolder."""
    print(f"Finding best CV for: {url}")
    
    # 1. Extract Job Description JSON (with Cache Intercept)
    cache = get_user_cache(user_id)
    cached_url = cache.get("last_jd_url", "")
    cached_jd_data = cache.get("last_jd_data", "")

    if url == cached_url and cached_jd_data:
        print("⚡ Found JD data in cache. Skipping extraction.")
        job_data = cached_jd_data
    else:
        extract_task = Task(
            description=f"Scrape the website at {url}. Return a JSON object with exactly three keys: 'Description', 'Requirements', and 'Responsibilities'. Return ONLY the raw JSON string.",
            expected_output="A valid JSON string.",
            agent=extractor_agent
        )
    extractor_crew = Crew(agents=[extractor_agent], tasks=[extract_task], verbose=False, max_rpm=10)
    try:
        job_data = run_crew_with_backoff(extractor_crew)
    except Exception as e:
        print(f"Traffic spike detected. Switching Extractor to fallback model... Error: {e}")
        extractor_agent.llm = gemini_pro
        try:
            job_data = run_crew_with_backoff(extractor_crew)
        except Exception:
            return "⚠️ **Match Interrupted**\nGoogle APIs are overloaded (Error 503). Please try again later."
        
    # 2. Route Job (DEV vs MGMT) to determine which subfolder to check
    route_task = Task(
        description=f"Analyze this job data: {job_data}. If it requires writing code/software engineering, output 'DEV'. If it requires overseeing projects or operations, output 'MGMT'. Output ONLY the word DEV or MGMT.",
        expected_output="Either the exact string 'DEV' or 'MGMT'.",
        agent=router_agent
    )
    router_crew = Crew(agents=[router_agent], tasks=[route_task], verbose=False, max_rpm=10)
    try:
        track = run_crew_with_backoff(router_crew).upper()
    except Exception as e:
        print(f"Traffic spike detected. Switching Router to fallback model... Error: {e}")
        router_agent.llm = gemini_pro
        try:
            track = run_crew_with_backoff(router_crew).upper()
        except Exception:
            track = "DEV" # Default safe fallback if totally blocked    
    selected_track = "DEV" if "DEV" in track else "MGMT"

    # 3. Build Lightweight CV Index from the targeted subfolder
    folder_path = os.path.join("O-output", selected_track)
    if not os.path.exists(folder_path) or not os.listdir(folder_path):
        return f"❌ No existing CVs found in the '{selected_track}' folder to match against. Generate some first."

    cv_index = ""
    for filename in os.listdir(folder_path):
        if filename.endswith(".md"):
            with open(os.path.join(folder_path, filename), "r", encoding="utf-8") as f:
                content = f.read()
                # Extract the profile summary for a lightweight read
                try:
                    profile_start = content.index("## Profile Summary") + len("## Profile Summary")
                    profile_end = content.index("---", profile_start)
                    summary = content[profile_start:profile_end].strip()
                    cv_index += f"\nFile: {filename}\nProfile Summary: {summary}\n"
                except ValueError:
                    cv_index += f"\nFile: {filename}\nProfile Summary: [Parsing Error - Profile not found]\n"

    # 4. Evaluate and Select using the Reviewer Agent
    match_task = Task(
        description=f"""
        Job Description Data: {job_data}
        
        Available CVs in the '{selected_track}' category:
        {cv_index}
        
        Evaluate the job requirements against the available CV summaries.
        Select the SINGLE best filename that matches this role. 
        Provide a brief justification explaining why this specific CV is the strongest fit.
        """,
        expected_output="The best matching filename and a short justification.",
        agent=reviewer_agent
    )
    
    match_crew = Crew(agents=[reviewer_agent], tasks=[match_task], verbose=False, max_rpm=10)
    
    try:
        result = run_crew_with_backoff(match_crew)
    except Exception as e:
        print(f"Traffic spike detected. Switching Reviewer to fallback model... Error: {e}")
        reviewer_agent.llm = gemini_flash
        try:
            result = run_crew_with_backoff(match_crew)
        except Exception:
            return "⚠️ **Match Interrupted**\nGoogle APIs are overloaded. Please try again later."

    # Update cache on success
    update_user_cache(user_id, {
        "last_jd_url": url,
        "last_generated_cv_name": result,
        "last_jd_data": job_data
    })
    
    return result