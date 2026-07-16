import os
import chromadb
from crewai import Task, Crew
from agents.config import gemini_pro, gemini_flash
from agents.agent_definitions import key_people_finder, personal_message_drafter, extractor_agent
from api.cache_manager import update_user_cache, get_user_cache
from utils.url_validator import validate_and_filter_urls
from utils.api_utils import run_crew_with_backoff

def run_people_finder(company, role, user_id):
    """Searches Google for LinkedIn profiles of recruiters and managers at the target company."""
    print(f"Finding key people at {company} for {role}...")
    
    cache = get_user_cache(user_id)
    query_key = f"{company}_{role}"
    if cache.get("last_people_query") == query_key and cache.get("last_found_people"):
        print("⚡ Found people in cache. Skipping search.")
        return cache.get("last_found_people")
    
    find_task = Task(
        description=f"""
        Use Google search (specifically targeting site:linkedin.com/in/) to find people who currently work at '{company}' in Israel.
        Look for two types of people related to the '{role}' position:
        1. Recruiters, Talent Acquisition, or HR.
        2. Hiring Managers, Engineering Managers, or Team Leads.
        
        Return a well-formatted WhatsApp message listing the names, their exact job titles, and their LinkedIn URLs.
        If you cannot find specific people for this role, find general technical recruiters for {company} in Israel.

        CRITICAL SYSTEM RULE: To avoid memory overload, you must strictly analyze the first batch of search results provided. Do not execute back-to-back searches unless absolutely necessary. Rely on the snippets provided in the first action.
        """,
        expected_output="A bulleted list of people, their roles, and LinkedIn URLs.",
        agent=key_people_finder
    )

    crew = Crew(agents=[key_people_finder], tasks=[find_task], verbose=False, max_rpm=10)
    
    try:
        result = run_crew_with_backoff(crew)
        result = validate_and_filter_urls(result)
        # Save the raw text of found people to cache
        update_user_cache(user_id, {
            "last_found_people": result,
            "last_people_query": query_key
        })
        
        return result
    except Exception as e:
        print(f"Traffic spike detected. Switching People Finder to fallback model... Error: {e}")
        key_people_finder.llm = gemini_flash
        try:
            result = run_crew_with_backoff(crew)
            result = validate_and_filter_urls(result)
            update_user_cache(user_id, {
                "last_found_people": result,
                "last_people_query": query_key
            })
            return result
        except Exception:
            return "⚠️ **Search Interrupted**\nGoogle APIs are overloaded. Please try again later."


def run_message_drafter(linkedin_url, jd_url, cv_search_term, user_id):
    """Drafts a personalized outreach message based on the target profile, JD, CV, and core rules."""
    print(f"Drafting message for {linkedin_url}...")
    
    # Safely handle NoneType if the parser missed the CV term
    cv_search_term = str(cv_search_term) if cv_search_term else ""
    search_words = [word.lower() for word in cv_search_term.split() if word.strip()]
    
    if not search_words:
        return "❌ Please specify which CV to use in your request (e.g., 'using my Wiz CV')."
        
    # 1. Locate CV locally
    output_dir = "O-output"
    cv_text = "CV not found."
    
    if os.path.exists(output_dir):
        for root, dirs, files in os.walk(output_dir):
            for filename in files:
                if filename.endswith(".md") and any(word in filename.lower() for word in search_words):
                    with open(os.path.join(root, filename), "r", encoding="utf-8") as f:
                        cv_text = f.read()
                    break
            if cv_text != "CV not found.":
                break

    if cv_text == "CV not found.":
        return f"❌ Could not find a locally saved CV matching '{cv_search_term}' to use for context."

    # 2. Extract Job Description
    cache = get_user_cache(user_id)
    cached_url = cache.get("last_jd_url", "")
    cached_jd_data = cache.get("last_jd_data", "")

    if jd_url == cached_url and cached_jd_data:
        print("⚡ Found JD data in cache. Skipping extraction.")
        jd_data = cached_jd_data
    else:
        extract_task = Task(
            description=f"Scrape {jd_url}. Return a JSON string with 'Description' and 'Requirements'.",
            expected_output="A JSON string.",
            agent=extractor_agent
        )
    extractor_crew = Crew(agents=[extractor_agent], tasks=[extract_task], verbose=False, max_rpm=10)
    try:
        jd_data = run_crew_with_backoff(extractor_crew)
    except Exception as e:
        print(f"Traffic spike detected. Switching Extractor to fallback model... Error: {e}")
        extractor_agent.llm = gemini_pro
        try:
            jd_data = run_crew_with_backoff(extractor_crew)
        except Exception:
            jd_data = "Could not scrape JD due to server limits. Base the message generally on the CV."

    # 3. Load C-Core Context & Database Rules
    core_dir = os.path.join(os.getcwd(), "C-core")
    try:
        with open(os.path.join(core_dir, "guidelines.md"), "r", encoding="utf-8") as f: guidelines = f.read()
        with open(os.path.join(core_dir, "hallucinations.md"), "r", encoding="utf-8") as f: hallucinations = f.read()
        with open(os.path.join(core_dir, "qualifications.md"), "r", encoding="utf-8") as f: qualifications = f.read()
    except FileNotFoundError:
        guidelines, hallucinations, qualifications = "Not found.", "Not found.", "Not found."

    try:
        db_path = os.path.join(os.getcwd(), "chroma_db")
        chroma_client = chromadb.PersistentClient(path=db_path)
        rules_collection = chroma_client.get_or_create_collection(name="career_rules")
        rules_data = rules_collection.get()
        historical_rules = "\n- ".join(rules_data['documents']) if rules_data and rules_data.get('documents') else "No previous rules."
    except Exception:
        historical_rules = "Could not load database rules."

    # 4. Draft Message
    draft_task = Task(
        description=f"""
        Target Person's LinkedIn: {linkedin_url}
        Job Description Data: {jd_data}
        Candidate's CV: {cv_text}
        
        Candidate's General Qualifications: {qualifications}
        Writing Guidelines & Style Rules: {guidelines}
        Learned Database Rules: {historical_rules}
        Hallucination Blocklist (NEVER claim these): {hallucinations}
        
        1. Use your search tool to search the Target Person's LinkedIn URL on Google to read their public snippet (current role, past universities, past companies).
        2. Look for common ground between the Candidate's background (CV & Qualifications) and the Target Person.
        3. Draft TWO messages from the candidate to this person regarding the job opening:
           - Option 1: A short LinkedIn Connection Note (STRICTLY under 300 characters).
           - Option 2: A slightly longer InMail/Email message (around 100-150 words).
        
        CRITICAL RULES:
        - You MUST strictly obey the Writing Guidelines and Learned Database Rules for tone, style, and phrasing.
        - You MUST NEVER include anything listed in the Hallucination Blocklist.
        - Keep the tone professional, respectful, and not overly aggressive.
        """,
        expected_output="Two formatted text drafts (Option 1 and Option 2).",
        agent=personal_message_drafter
    )

    crew = Crew(agents=[personal_message_drafter], tasks=[draft_task], verbose=False, max_rpm=10)
    
    try:
        return run_crew_with_backoff(crew)
    except Exception as e:
        print(f"Traffic spike detected. Switching Drafter to fallback model... Error: {e}")
        personal_message_drafter.llm = gemini_flash
        try:
            return run_crew_with_backoff(crew)
        except Exception:
            return "⚠️ **Drafting Interrupted**\nGoogle APIs are overloaded. Please try again later."