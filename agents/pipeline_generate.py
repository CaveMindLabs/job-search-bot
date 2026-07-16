import os
import chromadb
from crewai import Task, Crew, Process
# Import only the agents this specific pipeline needs
from agents.agent_definitions import (
    hunter_agent, extractor_agent, router_agent, culture_scout, 
    keyword_agent, strategist, tailor, gatekeeper
)
from agents.config import gemini_pro, gemini_flash  # For the 503 fallback
from api.cache_manager import update_user_cache, get_user_cache
from utils.api_utils import run_crew_with_backoff


def run_job_search_pipeline(user_input, company_name, user_id):
    """Executes the End-to-End CV Generation Pipeline."""
    
    # 1. Job Hunter Logic (Find the URL)
    if "http" not in user_input:
        print("No link detected. Initiating Hunter Agent...")
        hunter_task = Task(
            description=f"Search the web to find the active job posting URL for this request: '{user_input}'. Return ONLY the raw web URL. Do not return any other text.",
            expected_output="A single URL string starting with http.",
            agent=hunter_agent
        )
        url = str(Crew(agents=[hunter_agent], tasks=[hunter_task], max_rpm=10).kickoff().raw).strip()
    else:
        url = user_input

    # 2. Extractor Logic (Scrape the JSON with Cache Intercept and 503 Fallback)
    cache = get_user_cache(user_id)
    cached_url = cache.get("last_jd_url", "")
    cached_jd_data = cache.get("last_jd_data", "")

    if url == cached_url and cached_jd_data:
        print("⚡ Found JD data in cache. Skipping extraction.")
        job_data = cached_jd_data
    else:
        print(f"Extracting data from: {url}")
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
            raise Exception("Server overload while extracting JD (Error 503). Please try again.")

    # 3. Router Logic (DEV vs MGMT)
    print("Routing job description...")
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
            raise Exception("⚠️ Pipeline aborted: The Router Agent encountered continuous server limits (Error 503).")

    if "DEV" in track:
        selected_track = "DEV"
        template_path = "C-core/CV_Vault/Dev_Base.md"
    else:
        selected_track = "MGMT"
        template_path = "C-core/CV_Vault/Management_Base.md"

    # 4. Prepare Database Context (History, Rules, and COMPANY VALUES)
    safe_company_name = "".join(c for c in company_name if c.isalnum() or c in (' ', '_', '-')).strip()
    
    # Extract just the base company name (e.g., from "Amazon_Software_Engineer", get "Amazon")
    base_company = safe_company_name.split('_')[0] if '_' in safe_company_name else safe_company_name

    db_path = os.path.join(os.getcwd(), "chroma_db")
    chroma_client = chromadb.PersistentClient(path=db_path)
    
    career_data = chroma_client.get_or_create_collection(name="career_history").get()
    rules_data = chroma_client.get_or_create_collection(name="career_rules").get()
    historical_rules = "\n- ".join(rules_data['documents']) if rules_data and rules_data.get('documents') else "No previous rules."

    # Company Values Retrieval & Scouting Logic ---
    values_collection = chroma_client.get_or_create_collection(name="company_values")
    existing_values = values_collection.get(ids=[base_company])
    
    if existing_values and existing_values.get('documents') and len(existing_values['documents']) > 0:
        print(f"Company values for {base_company} found in database.")
        company_values_text = existing_values['documents'][0]
    else:
        print(f"Company values for {base_company} not found. Initiating Culture Scout...")
        scout_task = Task(
            description=f"""
            Search the web for the official core values, mission statement, or leadership principles of {base_company}. 
            If you find them, extract them into a concise bulleted list. 
            If you absolutely cannot find any specific core values after searching, return exactly this string: "No explicit core values found."
            """,
            expected_output="A bulleted list of core values, or the exact string 'No explicit core values found.'",
            agent=culture_scout
        )
        
        scout_crew = Crew(agents=[culture_scout], tasks=[scout_task], verbose=False, max_rpm=10)
        
        try:
            company_values_text = run_crew_with_backoff(scout_crew)
        except Exception as e:
            print(f"Traffic spike detected. Switching Culture Scout to fallback model... Error: {e}")
            culture_scout.llm = gemini_pro
            try:
                company_values_text = run_crew_with_backoff(scout_crew)
            except Exception as inner_e:
                raise Exception("⚠️ Pipeline aborted: The Culture Scout encountered continuous server limits (Error 503).")
        
        # Save to DB (even if empty placeholder) to prevent future redundant searches
        values_collection.add(
            documents=[company_values_text],
            metadatas=[{"company": base_company}],
            ids=[base_company]
        )
        print(f"Saved company values for {base_company} to database.")

    guide_path = os.path.join(os.getcwd(), "C-core", "guidelines.md")
    hallucination_path = os.path.join(os.getcwd(), "C-core", "hallucinations.md") # Add this
    
    try:
        with open(guide_path, "r", encoding="utf-8") as f:
            guidelines = f.read()
        with open(hallucination_path, "r", encoding="utf-8") as f:
            hallucinations = f.read()
    except FileNotFoundError:
        guidelines = "No guidelines found."
        hallucinations = "No specific hallucinations to avoid."

    # ATS Keyword Extraction ---
    print("Extracting ATS keywords from job description...")
    keyword_task = Task(
        description=f"Analyze this job data: {job_data}. Extract the 10-15 most critical technical keywords, hard skills, and domain terms. Return ONLY a comma-separated list of these keywords.",
        expected_output="A comma-separated string of keywords.",
        agent=keyword_agent
    )
    keyword_crew = Crew(agents=[keyword_agent], tasks=[keyword_task], verbose=False, max_rpm=10)
    try:
        keyword_list = run_crew_with_backoff(keyword_crew)
        print(f"Extracted Keywords: {keyword_list}")
    except Exception as e:
        print(f"Traffic spike detected. Switching Keyword Agent to fallback model... Error: {e}")
        keyword_agent.llm = gemini_pro
        try:
            keyword_list = run_crew_with_backoff(keyword_crew)
            print(f"Extracted Keywords: {keyword_list}")
        except Exception:
            raise Exception("⚠️ Pipeline aborted: The Keyword Agent encountered continuous server limits (Error 503).")

   # 5. Main Generation Crew
    build_context = Task(
        description=f"""
        Track: {selected_track}
        Job Details: {job_data}
        Career History: {career_data}
        Rules: {historical_rules}
        Company Core Values: {company_values_text}
        Writing Guidelines: {guidelines}
        Hallucination Blocklist: {hallucinations}
        
        Create a Context Packet emphasizing metrics and strictly applying the rules and writing guidelines. 
        CRITICAL: You must NEVER include information found in the Hallucination Blocklist.
        CRITICAL: You must actively align the candidate's career history framing with the provided Company Core Values.
        """,
        expected_output="A structured Context Packet.",
        agent=strategist
    )

    draft_blocks = Task(
        description=f"""
        Using the Context Packet and the Writing Guidelines ({guidelines}), write the tailored replacement markdown text for EVERY bracket: [[PROFILE]], [[SKILLS]], [[PROJ_WHATSAPP]], [[PROJ_HOTSPOTTER]], [[PROJ_BACKGAMMON]], [[PROJ_EFFICIENCY]], [[EXP_COO]], [[EXP_INSTRUCTOR]], [[EXP_OFFICER]], [[EDUCATION]].
        
        Target Keywords to include naturally: {keyword_list}
        
        CRITICAL IDENTITY RULE: You may frame achievements creatively, add realistic metrics, and detail technical sub-tasks (like version control or QA workflows) to match the JD. However, you MUST retain the exact high-level job titles (e.g., Operations Manager, Chief Operating Officer) and company structures provided in the history. Do not claim direct employment at partner companies like IAI.

        PROFILE SUMMARY RULE: When drafting the [[PROFILE]] block, you MUST end the summary with a tailored "why I want this job" / career objective sentence. This sentence should align with the core themes of the job description (e.g., leading technical teams, building scalable backend systems) without explicitly naming the target company or the exact job title.
        
        CRITICAL: Ensure all bullet points follow the Google XYZ formula and Claim+Evidence structure defined in the guidelines. Do not invent new markdown headers.
        Ensure the tone and phrasing reflect the Company Core Values ({company_values_text}). Weave the target keywords seamlessly into the bullet points.
        """,
        expected_output="A list pairing tags with bullet points.",
        agent=tailor
    )

    # Ensure the specific track subfolder exists
    os.makedirs(f"O-output/{selected_track}", exist_ok=True)

    finalize = Task(
        description=f"""
        Read template '{template_path}'. Substitute the text blocks generated by the Tailor into their corresponding tags.
        
        Target Keywords: {keyword_list}
        Candidate Master History: {career_data}
        
        CONTRADICTION AUDIT REQUIREMENT:
        Review the drafted blocks against the Candidate Master History before finalizing. 
        1. ALLOW plausible framing, advanced technical sub-tasks (like version control, debugging workflows), and realistic metric generation that aligns with the role.
        2. STRICTLY FORBID and fix direct structural contradictions: the candidate's official job titles (e.g., Operations Manager, COO), actual employment dates, and true company contexts must remain 100% accurate to the Master History. Never let the text imply he was directly employed as a 'Software Engineer' or worked 'for' an external partner like IAI if the history states he was an Operations Manager coordinating with them.
        3. MANDATORY: Ensure the personal contact details block at the very top of the CV template remains completely untouched.
        4. PROFILE VERIFICATION: Check the Profile Summary block. It MUST end with a forward-looking "career objective" sentence that broadly aligns with the job's themes (e.g., aiming to lead technical teams, or seeking to architect scalable systems) without explicitly naming the company. If it is missing, seamlessly append one.
        
        Keep the Markdown structure exactly as is.
        """,
        expected_output="The final properly formatted and audited Markdown resume.",
        agent=gatekeeper,
        output_file=f"O-output/{selected_track}/{safe_company_name}.md"
    )

    cv_crew = Crew(
        agents=[strategist, tailor, gatekeeper], 
        tasks=[build_context, draft_blocks, finalize], 
        process=Process.sequential,
        max_rpm=10  # Limits requests to 10 per minute
    )
    os.makedirs("O-output", exist_ok=True)
    
    try:
        result = run_crew_with_backoff(cv_crew)
        
        # Save to cache on success
        update_user_cache(user_id, {
            "last_generated_cv_path": f"O-output/{selected_track}/{safe_company_name}.md",
            "last_generated_cv_name": safe_company_name,
            "last_jd_keywords": keyword_list,
            "last_jd_url": url,
            "last_jd_data": job_data
        })
        
        return result
    except Exception as e:
        print(f"Traffic spike detected. Switching Generation Crew to fallback model... Error: {e}")
        # Swap all reasoning agents to the lighter model
        strategist.llm = gemini_flash
        tailor.llm = gemini_flash
        gatekeeper.llm = gemini_flash
        try:
            result = run_crew_with_backoff(cv_crew)
            
            # Save to cache on success
            update_user_cache(user_id, {
                "last_generated_cv_path": f"O-output/{selected_track}/{safe_company_name}.md",
                "last_generated_cv_name": safe_company_name,
                "last_jd_keywords": keyword_list,
                "last_jd_url": url,
                "last_jd_data": job_data
            })
            
            return result
        except Exception as inner_e:
            return "⚠️ **Generation Interrupted**\nI encountered continuous server limits (Error 503). Please wait a moment and try again."