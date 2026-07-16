"""
agents/utility_agents.py
Contains isolated agents for parsing intents, extracting rules, and managing the database.
"""
import json
import uuid
import os
import chromadb
from crewai import Agent, Task, Crew
from agents.config import gemini_flash, gemini_pro
from api.cache_manager import get_user_cache
from utils.api_utils import run_crew_with_backoff

# --- 1. THE PARSER ---

def parse_whatsapp_message(message_text, user_id):
    """Determines user intent and extracts parameters."""
    cache = get_user_cache(user_id)
    parser_agent = Agent(
        role="Message Router",
        goal="Analyze text to determine user intent and extract parameters.",
        backstory="You route messages for a backend job search pipeline.",
        llm=gemini_flash,
        verbose=False
    )
    
    parse_task = Task(
        description=f"""
        Analyze this message: "{message_text}"

        Session Memory Cache Context (Use this to resolve pronouns like "that", "the last one", "her", "him"):
        - Last JD URL: {cache.get('last_jd_url', 'None')}
        - Last Generated CV File Name: {cache.get('last_generated_cv_name', 'None')}
        - Last Found People: {cache.get('last_found_people', 'None')}
        - Last Found Jobs: {cache.get('last_found_jobs', 'None')}  <-- ADD THIS LINE

        Determine the intent from these 13 options:
        1. "CV": Generate a new CV.
        2. "FEEDBACK": Save interview/search feedback to learn a new rule.
        3. "RETRIEVE": Get, read, or find a previously generated CV file.
        4. "SEARCH_JOBS": Find open job positions on the web.
        5. "DB_MANAGE": The user wants to see/read OR edit the existing Company Values or Learned Rules in the database.
        6. "REVIEW_CV": The user wants to review or score a previously generated CV against a specific job URL.
        7. "FIND_BEST_CV": The user wants the bot to read a job URL and select the best existing CV from the output folder.
        8. "IMPLEMENT_REVIEW": The user is answering "yes" or agrees to implement CV review changes.
        9. "REJECT_REVIEW": The user is answering "no" or declines to implement CV review changes.
        10. "FIND_PEOPLE": The user wants to find recruiters or managers at a company for a specific role.
        11. "DRAFT_MESSAGE": The user wants to write a networking message to a specific person.
        12. "SHOW_COMMANDS": The user is asking for help, what the bot can do, or a list of available commands.
        13. "EXTRACT_KEYWORDS": The user wants keywords from a specific URL.
        
        Return ONLY a raw JSON string:
        If CV: {{"intent": "CV", "company": "CompanyName", "role": "JobTitle", "url": "URL if available from cache or text"}}
        If Feedback: {{"intent": "FEEDBACK", "company": "CompanyName or 'General Search'", "good_feedback": "...", "bad_feedback": "..."}}
        If Retrieve: {{"intent": "RETRIEVE", "search_term": "..."}}
        If Search Jobs: {{"intent": "SEARCH_JOBS", "query": "..."}}
        If DB Manage: {{"intent": "DB_MANAGE", "target": "VALUES" or "RULES", "action": "READ" or "EDIT", "company_name": "Company name or null", "edit_instruction": "The edit instruction or null"}}
        If Review CV: {{"intent": "REVIEW_CV", "search_term": "name of company or role", "url": "http..."}}
        If Find Best CV: {{"intent": "FIND_BEST_CV", "url": "http..."}}
        If Implement Review: {{"intent": "IMPLEMENT_REVIEW"}}
        If Reject Review: {{"intent": "REJECT_REVIEW"}}
        If Find People: {{"intent": "FIND_PEOPLE", "company": "Company Name", "role": "Job Title"}}
        If Draft Message: {{"intent": "DRAFT_MESSAGE", "linkedin_url": "url of person", "jd_url": "url of job", "cv_search_term": "name of cv"}}
        If Show Commands: {{"intent": "SHOW_COMMANDS"}}
        If Extract Keywords: {{"intent": "EXTRACT_KEYWORDS", "url": "http..."}}
        """,
        expected_output="A raw JSON string.",
        agent=parser_agent
    )
    
    crew = Crew(agents=[parser_agent], tasks=[parse_task], verbose=False, max_rpm=10)
    
    try:
        result = run_crew_with_backoff(crew)
    except Exception as e:
        print(f"Traffic spike detected. Switching Parser to fallback model... Error: {e}")
        parser_agent.llm = gemini_pro
        try:
            result = run_crew_with_backoff(crew)
        except Exception:
            return {"intent": "ERROR", "message": "Servers are overloaded. Please try again in a minute."}
            
    result = result.replace("```json", "").replace("```", "").strip()
    
    try:
        return json.loads(result)
    except Exception as e:
        print(f"Failed to parse JSON: {e}")
        return {"intent": "CV", "company": "Unknown", "role": "Unknown"}


# --- 2. THE DB EDITOR ---

db_editor_agent = Agent(
    role="Database Editor",
    goal="Safely modify database entries based on natural language instructions.",
    backstory="You are a precise data administrator. You rewrite text while retaining core information.",
    llm=gemini_flash,
    verbose=True
)

def manage_database(target, action, company_name=None, edit_instruction=None):
    """Retrieves or edits records in ChromaDB based on LLM instructions."""
    db_path = os.path.join(os.getcwd(), "chroma_db")
    chroma_client = chromadb.PersistentClient(path=db_path)

    if target == "VALUES":
        collection = chroma_client.get_or_create_collection("company_values")
        if not company_name:
            return "❌ Please specify a company name to check its values."

        base_company = company_name.split('_')[0] if '_' in company_name else company_name
        existing = collection.get(ids=[base_company])
        
        if not existing or not existing.get('documents') or len(existing['documents']) == 0:
            return f"❌ No values found in the database for {base_company}."

        current_values = existing['documents'][0]

        if action == "READ":
            return f"🏢 **Values for {base_company}:**\n\n{current_values}"

        elif action == "EDIT":
            edit_task = Task(
                description=f"Current values: {current_values}\nInstruction: {edit_instruction}\nRewrite the values based on this instruction.",
                expected_output="The rewritten core values.",
                agent=db_editor_agent
            )
            edit_crew = Crew(agents=[db_editor_agent], tasks=[edit_task], verbose=False, max_rpm=10)
            try:
                new_values = run_crew_with_backoff(edit_crew)
            except Exception as e:
                print(f"Traffic spike detected. Switching DB Editor to fallback model... Error: {e}")
                db_editor_agent.llm = gemini_pro
                try:
                    new_values = run_crew_with_backoff(edit_crew)
                except Exception:
                    return "❌ Error updating database. Google APIs are currently overloaded."   
                         
            # Upsert automatically overwrites the old entry since the ID is the same
            collection.upsert(documents=[new_values], metadatas=[{"company": base_company}], ids=[base_company])
            return f"✅ **Updated {base_company} Values:**\n\n{new_values}"

    elif target == "RULES":
        collection = chroma_client.get_or_create_collection("career_rules")
        existing = collection.get()

        if not existing or not existing.get('documents'):
            return "❌ No learned rules found in the database."

        if action == "READ":
            rules_str = ""
            for i, doc in enumerate(existing['documents']):
                rules_str += f"{i+1}. {doc}\n"
            return f"🧠 **Current Learned Rules:**\n\n{rules_str}"

        elif action == "EDIT":
            # Pass rules + IDs to the LLM so it knows exactly which one to delete or update
            rules_data = [{"id": doc_id, "text": doc} for doc_id, doc in zip(existing['ids'], existing['documents'])]
            
            edit_task = Task(
                description=f"Current rules: {json.dumps(rules_data)}\nInstruction: {edit_instruction}\nDetermine which rules to update or delete. Return ONLY a JSON list of actions: [{{'action': 'delete', 'id': '...', 'text': '... '}}, {{'action': 'update', 'id': '...', 'text': 'new text'}}]",
                expected_output="A raw JSON string of actions.",
                agent=db_editor_agent
            )
            edit_crew = Crew(agents=[db_editor_agent], tasks=[edit_task], verbose=False, max_rpm=10)
            try:
                response = run_crew_with_backoff(edit_crew)
            except Exception as e:
                print(f"Traffic spike detected. Switching DB Editor to fallback model... Error: {e}")
                db_editor_agent.llm = gemini_pro
                try:
                    response = run_crew_with_backoff(edit_crew)
                except Exception:
                    return "❌ Error updating database. Google APIs are currently overloaded."
            response = response.replace("```json", "").replace("```", "").strip()

            try:
                actions = json.loads(response)
                summary_report = "✅ **Database Update Report:**\n\n"
                
                for act in actions:
                    if act['action'] == 'delete':
                        collection.delete(ids=[act['id']])
                        summary_report += f"🗑️ **Deleted Rule:** {act['text']}\n"
                    elif act['action'] == 'update':
                        collection.upsert(ids=[act['id']], documents=[act['text']])
                        summary_report += f"📝 **Updated Rule to:** {act['text']}\n"
                
                return summary_report
            except Exception as e:
                return f"❌ Failed to parse DB update. Ensure instruction is clear."

# --- 3. CLOSE THE LOOP ---
def run_close_the_loop(company_name, outcome, good_feedback, bad_feedback):
    loop_closer = Agent(
        role="Feedback Analyzer & Knowledge Extractor",
        goal="Extract actionable rules from user feedback.",
        backstory="You analyze job application outcomes and search feedback. You distill feedback into strict, single-sentence rules to improve future agent behavior.",
        llm=gemini_flash,
        verbose=True
    )
    analyze_feedback = Task(
        description=f"Company/Topic: {company_name}\nOutcome/Context: {outcome}\nGood: {good_feedback}\nBad/Adjust: {bad_feedback}\nExtract exactly one concrete rule.",
        expected_output="A single clear sentence.",
        agent=loop_closer
    )
    crew = Crew(agents=[loop_closer], tasks=[analyze_feedback], verbose=False, max_rpm=10)
    
    try:
        extracted_rule = run_crew_with_backoff(crew)
    except Exception as e:
        print(f"Traffic spike detected. Switching Loop Closer to fallback model... Error: {e}")
        loop_closer.llm = gemini_pro
        try:
            extracted_rule = run_crew_with_backoff(crew)
        except Exception as inner_e:
            return "⚠️ **Feedback Interrupted**\nGoogle APIs are currently overloaded. Please try again later."

    # Only save to DB if it successfully extracted a rule (didn't return an error message)
    db_path = os.path.join(os.getcwd(), "chroma_db")
    chroma_client = chromadb.PersistentClient(path=db_path)
    rules_collection = chroma_client.get_or_create_collection(name="career_rules")
    rules_collection.add(
        documents=[extracted_rule],
        metadatas=[{"company": company_name, "outcome": outcome}],
        ids=[f"rule_{uuid.uuid4().hex[:8]}"]
    )
    return extracted_rule