"""
agents/pipeline_agents.py
Executes the main End-to-End CV Review pipeline.
"""
import os
from crewai import Task, Crew
# Import only the agents this specific pipeline needs
from agents.agent_definitions import extractor_agent, reviewer_agent, cv_editor_agent
from agents.config import gemini_pro, gemini_flash
from api.cache_manager import update_user_cache, get_user_cache
from utils.api_utils import run_crew_with_backoff


def run_cv_review_pipeline(cv_search_term, url, user_id):
    """Scores a generated CV against a Job Description URL."""
    print(f"Starting CV Review for: '{cv_search_term}' against {url}")
    
# 1. Find and Read the CV File locally (Recursive + Flexible Word Matching)
    output_dir = "O-output"
    cv_text = "CV not found."
    search_words = [word.lower() for word in cv_search_term.split() if word.strip()]
    found_filepath = None
    
    if os.path.exists(output_dir):
        for root, dirs, files in os.walk(output_dir):
            for filename in files:
                if filename.endswith(".md"):
                    filename_lower = filename.lower()
                    if any(word in filename_lower for word in search_words):
                        found_filepath = os.path.join(root, filename)
                        with open(found_filepath, "r", encoding="utf-8") as f:
                            cv_text = f.read()
                        print(f"Found CV for Review: {filename} in {root}")
                        break
            if cv_text != "CV not found.":
                break

    if not found_filepath:
        return f"❌ Could not find a CV matching '{cv_search_term}' in the output folders.", None

    # 2. Extract JD JSON
    print(f"Checking cache for job data: {url}")
    cache = get_user_cache(user_id)
    cached_url = cache.get("last_jd_url", "")
    cached_jd_data = cache.get("last_jd_data", "")

    if url == cached_url and cached_jd_data:
        print("⚡ Found JD data in cache. Skipping extraction.")
        job_data = cached_jd_data
    else:
        print(f"Extracting job data from: {url}")
        extract_task = Task(
            description=f"Scrape the website at {url}. Return a JSON object with exactly three keys: 'Description', 'Requirements', and 'Responsibilities'. Return ONLY the raw JSON string.",
            expected_output="A valid JSON string.",
            agent=extractor_agent
        )
    
    extractor_crew = Crew(agents=[extractor_agent], tasks=[extract_task], verbose=False, max_rpm=10)
    
    try:
        # Try running the extractor with automatic backoff retries
        job_data = run_crew_with_backoff(extractor_crew)
    except Exception as e:
        # If it fails 3 times, switch model to gemini_pro and try again with backoff
        print(f"Traffic spike detected. Switching Extractor to fallback model... Error: {e}")
        extractor_agent.llm = gemini_pro
        try:
            job_data = run_crew_with_backoff(extractor_crew)
        except Exception as inner_e:
            return "⚠️ **Review Interrupted**\nServer limits exceeded while extracting the JD. Please try again later.", None

    # 3. Load C-Core Context for Correctness Scoring
    core_dir = os.path.join(os.getcwd(), "C-core")
    try:
        with open(os.path.join(core_dir, "hallucinations.md"), "r", encoding="utf-8") as f:
            hallucinations = f.read()
        with open(os.path.join(core_dir, "career_master.json"), "r", encoding="utf-8") as f:
            career_master = f.read()
    except FileNotFoundError:
        hallucinations, career_master = "Not found.", "Not found."

    # 4. Execute Review
    print("Executing ATS Review...")
    review_task = Task(
        description=f"""
        Job Description Data: {job_data}
        
        Candidate CV: 
        {cv_text}
        
        Hallucination Blocklist: {hallucinations}
        Master Career History: {career_master}
        
        Perform a strict ATS and Recruiter audit using the following 4-Pillar Scoring Rubric (Out of 10.0):
        
        1. Keyword Density & ATS Optimization (Max 3.0): 3.0 = High density; 1.5 = Moderate; 0.0 = Poor.
        2. Hard Skill Match (Max 3.0): 3.0 = All mandatory met; 1.5 = Missing 1-2; 0.0 = Critical gaps.
        3. Experience & Seniority Alignment (Max 2.0): 2.0 = Perfect match; 1.0 = Slight mismatch; 0.0 = Complete disconnect.
        4. C-Core Correctness & Format (Max 2.0): 2.0 = Zero blocklist hits, strong metrics, matches Master History. Deduct all 2.0 points if ANY hallucination from the blocklist is used.
        
        Provide a structured review formatted EXACTLY like this:
        - **Keywords (X.X/3.0):** [One sentence justification]
        - **Skills (X.X/3.0):** [One sentence justification]
        - **Experience (X.X/2.0):** [One sentence justification]
        - **Correctness (X.X/2.0):** [One sentence justification]
        - **Total ATS Score:** [Total]/10.0
        
        After the score breakdown, provide:
        - **Strengths:** [Brief bullet points]
        - **Weaknesses/Missing Items:** [Critical gaps]
        - **Actionable Recommendations:** [Specific changes for the editor to implement]

        CRITICAL: Keep your entire response concise. You must strictly limit your output to under 3,000 characters. Be direct and to the point.
        """,
        expected_output="A structured review following the 4-Pillar format.",
        agent=reviewer_agent
    )
    
    # Run the crew and get the result
    reviewer_crew = Crew(agents=[reviewer_agent], tasks=[review_task], verbose=False, max_rpm=10)
    
    try:
        # Try running the review task with automatic backoff retries
        result = run_crew_with_backoff(reviewer_crew)
    except Exception as e:
        # Fallback to gemini_flash if pro is overloaded
        print(f"Traffic spike detected. Switching Reviewer to fallback model... Error: {e}")
        reviewer_agent.llm = gemini_flash
        try:
            result = run_crew_with_backoff(reviewer_crew)
        except Exception:
            return "⚠️ **Review Interrupted**\nServer limits exceeded during the ATS review. Please try again later.", None    
    # Update the cache
    update_user_cache(user_id, {
        "last_jd_url": url,
        "last_generated_cv_path": found_filepath,
        "last_jd_data": job_data,
        "last_cv_review": result
    })
    
    return result, found_filepath

def run_implement_review_pipeline(cv_filepath, review_text):
    """Rewrites a CV based on ATS review recommendations."""
    print(f"Implementing review for {cv_filepath}")
    
    with open(cv_filepath, "r", encoding="utf-8") as f:
        cv_text = f.read()
        
    edit_task = Task(
        description=f"""
        Original CV Markdown:
        {cv_text}
        
        Review Recommendations to Implement:
        {review_text}
        
        Task: Rewrite the Original CV to fix the weaknesses and implement the recommendations.
        
        CRITICAL: 
        1. You must output ONLY the fully updated raw Markdown text. 
        2. Do not add conversational filler (e.g., "Here is your updated CV").
        3. Keep the exact same Markdown structure, brackets, and headers.
        """,
        expected_output="The fully updated, raw Markdown CV.",
        agent=cv_editor_agent
    )
    
    edit_crew = Crew(agents=[cv_editor_agent], tasks=[edit_task], verbose=False, max_rpm=10)
    
    try:
        # Try to rewrite the CV using backoff retries
        new_cv = run_crew_with_backoff(edit_crew)
    except Exception as e:
        # If it fails 3 times, switch to gemini_flash and try again with backoff
        print(f"Traffic spike detected. Switching Editor to fallback model... Error: {e}")
        cv_editor_agent.llm = gemini_flash
        try:
            new_cv = run_crew_with_backoff(edit_crew)
        except Exception as inner_e:
            return "⚠️ **Edit Interrupted**\nServer limits exceeded while rewriting the CV. Please try again later."
    
    # Strip accidental code blocks from LLM output
    if new_cv.startswith("```markdown"):
        new_cv = new_cv[11:]
    if new_cv.endswith("```"):
        new_cv = new_cv[:-3]
        
    # Overwrite original file
    with open(cv_filepath, "w", encoding="utf-8") as f:
        f.write(new_cv.strip())
        
    filename = os.path.basename(cv_filepath)
    return f"✅ Successfully implemented the changes. The file `{filename}` has been updated.\n\nYou can reply with 'Get CV: {filename}' to see the updated version."