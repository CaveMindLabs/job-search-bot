# api/message_processor.py
import re
import asyncio
from agents.pipeline_keywords import run_keyword_extraction_only
from services.memory_store import memory_store
from services.whatsapp_service import send_whatsapp_message
from services.file_manager import search_local_cvs, get_cv_content
from agents.utility_agents import parse_whatsapp_message, run_close_the_loop, manage_database
from agents.pipeline_generate import run_job_search_pipeline
from agents.pipeline_prospect import run_job_prospector
from agents.pipeline_review import run_cv_review_pipeline, run_implement_review_pipeline
from agents.pipeline_match import run_best_cv_match_pipeline
from utils.logging import log_message_data
from agents.pipeline_network import run_people_finder, run_message_drafter
from agents.utility_agents import manage_database
from api.cache_manager import get_user_cache

pending_reviews = {}

async def list_available_models():
    return ["gemini-1.5-flash", "gemini-1.5-flash-lite"]

async def format_and_send_model_list(user_id: str):
    models = await list_available_models()
    if models:
        models.sort(key=lambda x: ('gpt-4o' not in x, 'mini' in x, x))
        formatted_list = "\n- ".join(models)
        reply_text = f"You can choose from these available models:\n\n- {formatted_list}\n\nTo select one, send a message like this:\n`/Use model: \"gemini-1.5-flash\"`\n\n"
        await send_whatsapp_message(to=user_id, text=reply_text)

async def process_and_reply(normalized_data: dict):
    user_id = normalized_data["user_id"]
    user_text = normalized_data["text"].strip()

    # Command Router
    model_selection_match = re.match(r'/Use model: [\'"]([^\'"]+)[\'"]', user_text, re.IGNORECASE)
    if model_selection_match:
        model_name = model_selection_match.group(1)
        available_models = await list_available_models()
        if model_name in available_models:
            memory_store.add_message(user_id, "user", user_text)
            memory_store.set_user_preference(user_id, 'model', model_name)
            await send_whatsapp_message(to=user_id, text=f"✅ Model for this chat is now set to `{model_name}`.")
        else:
            await send_whatsapp_message(to=user_id, text=f"❌ Sorry, the model `{model_name}` is not available.")
            await format_and_send_model_list(user_id)
        return  

    # Direct File Fetch Bypass
    if user_text.startswith("Get CV:"):
        filename = user_text.replace("Get CV:", "").strip()
        cv_content = get_cv_content(filename)
        if cv_content:
            await send_whatsapp_message(to=user_id, text=cv_content[:4000])
        else:
            await send_whatsapp_message(to=user_id, text=f"❌ Could not find the file: {filename}")
        log_message_data(normalized_data, "[Fetched specific CV]")
        return 

    await send_whatsapp_message(to=user_id, text="⚙️ Agent triggered! Processing your request. This might take a minute...")

    # Dynamic Intent Routing
    try:
        parsed_data = await asyncio.to_thread(parse_whatsapp_message, user_text, user_id)
        intent = parsed_data.get("intent", "CV")
        raw_company = parsed_data.get("company") # Safely handle potential None values to prevent 'NoneType' crashes
        company = str(raw_company).replace(" ", "_") if raw_company else "Unknown"
        
        if intent == "RETRIEVE":
            search_term = parsed_data.get("search_term", "")
            matches = search_local_cvs(search_term)
            if not matches:
                await send_whatsapp_message(to=user_id, text=f"🔍 No CVs found for '{search_term}'.")
            elif len(matches) == 1:
                content = get_cv_content(matches[0])
                await send_whatsapp_message(to=user_id, text=f"📄 Found it!\n\n{content[:4000]}")
            else:
                reply_msg = f"🔍 Found multiple matches. Text back the exact command:\n\n" + "\n".join([f"`Get CV: {m}`" for m in matches])
                await send_whatsapp_message(to=user_id, text=reply_msg)

        elif intent == "SEARCH_JOBS":
            # --- JOB PROSPECTING LOGIC ---
            search_query = parsed_data.get("query", user_text)
            await send_whatsapp_message(to=user_id, text=f"🔍 Scanning the web and LinkedIn for roles matching your resume... This will take a moment.")
            
            job_results = await asyncio.to_thread(run_job_prospector, search_query, user_id)
            
            # --- SANITY CHECK & ERROR INTERCEPT ---
            lower_results = job_results.lower()
            
            if job_results.startswith("⚠️") or job_results.startswith("❌"):
                await send_whatsapp_message(to=user_id, text=job_results)
            elif any(phrase in lower_results for phrase in ["let's do some more target searches", "let's see:", "final answer:", "remember, formatting counts"]):
                await send_whatsapp_message(to=user_id, text="⚠️ **Search Failed**\nThe agent encountered a server-side timeout. Please try again.")
            elif "http" not in lower_results:
                await send_whatsapp_message(to=user_id, text="⚠️ **Search Failed**\nThe agent failed to find any valid URLs. Please try rephrasing your search.")
            else:
                # Success path
                if len(job_results) > 4000:
                    job_results = job_results[:4000] + "\n\n...[Job results truncated]"
                
                success_message = f"Here are the most relevant positions I found:\n\n{job_results}\n\nReply with a specific link if you want me to draft a CV for it."
                await send_whatsapp_message(to=user_id, text=success_message)
                
        elif intent == "FEEDBACK":
            extracted_rule = await asyncio.to_thread(run_close_the_loop, company, "Feedback via WhatsApp", parsed_data.get("good_feedback", ""), parsed_data.get("bad_feedback", ""))
            
            # Check if the pipeline returned our custom error message
            if extracted_rule.startswith("⚠️") or extracted_rule.startswith("❌"):
                await send_whatsapp_message(to=user_id, text=extracted_rule)
            else:
                await send_whatsapp_message(to=user_id, text=f"🧠 Learned a new rule for {company}:\n_{extracted_rule}_")
            
        elif intent == "FIND_PEOPLE":
            company = parsed_data.get("company", "the company")
            role = parsed_data.get("role", "the role")
            await send_whatsapp_message(to=user_id, text=f"🔍 Scanning LinkedIn for recruiters and managers at {company}...")
            
            result = await asyncio.to_thread(run_people_finder, company, role, user_id)
            await send_whatsapp_message(to=user_id, text=result)

        elif intent == "DRAFT_MESSAGE":
            linkedin_url = parsed_data.get("linkedin_url", "")
            jd_url = parsed_data.get("jd_url", "")
            cv_search_term = parsed_data.get("cv_search_term", "")
            
            if not linkedin_url or not jd_url:
                await send_whatsapp_message(to=user_id, text="❌ Please provide both the person's LinkedIn URL and the Job URL.")
                return
                
            await send_whatsapp_message(to=user_id, text=f"✍️ Drafting personalized outreach message...")
            
            result = await asyncio.to_thread(run_message_drafter, linkedin_url, jd_url, cv_search_term, user_id)
            await send_whatsapp_message(to=user_id, text=result)
        
        elif intent == "REVIEW_CV":
            cv_search_term = parsed_data.get("search_term", "")
            url = parsed_data.get("url", "")
            
            if not url or "http" not in url:
                await send_whatsapp_message(to=user_id, text="❌ Please provide a valid URL for the job description.")
                return

            await send_whatsapp_message(to=user_id, text=f"🔍 Reviewing the '{cv_search_term}' CV against the job description...")
            
            # Note: We now expect a tuple back (the text, and the file path)
            review_response, cv_filepath = await asyncio.to_thread(
                run_cv_review_pipeline, 
                cv_search_term=cv_search_term, 
                url=url,
                user_id=user_id
            )
            
            if not cv_filepath:
                await send_whatsapp_message(to=user_id, text=review_response)
                return

            # Save the state so the bot knows what to edit if you say "yes"
            pending_reviews[user_id] = {
                "filepath": cv_filepath,
                "review_text": review_response
            }

            if len(review_response) > 3900:
                review_response = review_response[:3900] + "\n\n...[Review truncated due to WhatsApp length limits]"
            
            # Append the prompt
            review_response += "\n\n*Would you like me to implement these recommendations? Reply YES or NO.*"
            await send_whatsapp_message(to=user_id, text=review_response)

        elif intent == "IMPLEMENT_REVIEW":
            if user_id not in pending_reviews:
                await send_whatsapp_message(to=user_id, text="❌ I don't have a recent review pending. Please run a review first.")
                return
                
            state = pending_reviews[user_id]
            await send_whatsapp_message(to=user_id, text="✍️ Implementing the changes and rewriting your CV... This will take a moment.")
            
            result = await asyncio.to_thread(
                run_implement_review_pipeline,
                cv_filepath=state["filepath"],
                review_text=state["review_text"]
            )
            
            # Clear the state once done
            del pending_reviews[user_id]
            await send_whatsapp_message(to=user_id, text=result)

        elif intent == "REJECT_REVIEW":
            if user_id in pending_reviews:
                del pending_reviews[user_id]
            await send_whatsapp_message(to=user_id, text="Ok.")

        elif intent == "RETRIEVE_KEYWORDS":
            cache = get_user_cache(user_id)
            keywords = cache.get("last_jd_keywords")
            jd_url = cache.get("last_jd_url")
            
            if keywords:
                await send_whatsapp_message(
                    to=user_id, 
                    text=f"🔑 *Keywords for the last JD found ({jd_url}):*\n\n{keywords}"
                )
            else:
                await send_whatsapp_message(
                    to=user_id, 
                    text="❌ I couldn't find any cached keywords from your recent searches. Try generating a CV or searching for a job first!"
                )
        
        elif intent == "DB_MANAGE":
            # --- DATABASE MANAGEMENT LOGIC ---
            target = parsed_data.get("target")
            action = parsed_data.get("action")
            target_company = parsed_data.get("company_name")
            instruction = parsed_data.get("edit_instruction")

            await send_whatsapp_message(to=user_id, text=f"🗄️ Accessing database...")
            
            db_response = await asyncio.to_thread(
                manage_database, 
                target=target, 
                action=action, 
                company_name=target_company, 
                edit_instruction=instruction
            )
            await send_whatsapp_message(to=user_id, text=db_response)

        elif intent == "FIND_BEST_CV":
            url = parsed_data.get("url", "")
            
            if not url or "http" not in url:
                await send_whatsapp_message(to=user_id, text="❌ Please provide a valid URL for the job description.")
                return

            await send_whatsapp_message(to=user_id, text="🔍 Scanning your existing CVs to find the best match...")
            
            match_response = await asyncio.to_thread(
                run_best_cv_match_pipeline, 
                url=url,
                user_id=user_id
            )
            # Truncate to 4000 chars to ensure it passes WhatsApp's 4096 limit safely
            if len(match_response) > 4000:
                match_response = match_response[:4000] + "\n\n...[Match response truncated due to WhatsApp length limits]"
            await send_whatsapp_message(to=user_id, text=match_response)

        elif intent == "EXTRACT_KEYWORDS":
            url = parsed_data.get("url", "")
            if not url or "http" not in url:
                await send_whatsapp_message(to=user_id, text="❌ Please provide a valid URL.")
                return
            # --- CACHE INTERCEPT ---
            cache = get_user_cache(user_id)
            cached_url = cache.get("last_jd_url", "")
            cached_keywords = cache.get("last_jd_keywords", "")
            # If the requested URL matches the cached URL, return memory immediately
            if url == cached_url and cached_keywords:
                await send_whatsapp_message(to=user_id, text=f"⚡ *Found in Cache!*\n\n{cached_keywords}")
                return

            await send_whatsapp_message(to=user_id, text="🔍 Extracting keywords...")
            # Ensure the function is imported at the top of message_processor.py
            result = await asyncio.to_thread(run_keyword_extraction_only, url, user_id)
            await send_whatsapp_message(to=user_id, text=result)
            
        elif intent == "SHOW_COMMANDS":
            help_text = """*🤖 Available Bot Commands:*

*📝 CV & Applications*
• *Generate CV:* "Create a CV for [Company] as [Role] [Job URL]"
• *Review CV:* "Score my [Company] CV against this job: [URL]"
• *Find Best Match:* "Which CV fits this job best? [URL]"
• *Retrieve CV:* "Get my CV for [Company]"

*🔍 Prospecting & Networking*
• *Search Jobs:* "Find [Role] jobs in Israel"
• *Extract Keywords:* "Extract keywords from [URL]"
• *Find People:* "Find recruiters at [Company] for [Role]"
• *Draft Message:* "Draft a message to [LinkedIn URL] for [Job URL] using my [Company] CV"

*🧠 Memory & Database*
• *Add Feedback:* "I got rejected by [Company] because [Reason]. Add a rule to avoid this."
• *Manage DB:* "Show me my learned rules" OR "Show me values for [Company]"
• *Retrieve Keywords:* "Show me the keywords from the last job description I searched for"
"""
            await send_whatsapp_message(to=user_id, text=help_text)

        else:
            # Safely handle potential None values for the role
            raw_role = parsed_data.get("role")
            role = str(raw_role).replace(" ", "_").replace("/", "-") if raw_role else "Role"
            safe_name = f"{company}_{role}"
            
            # If the parser resolved a URL from the cache, append it to the text 
            # so the Hunter Agent sees it and skips the web search
            resolved_url = parsed_data.get("url")
            if resolved_url and "http" in resolved_url:
                user_text = f"{user_text} {resolved_url}"
                
            await asyncio.to_thread(run_job_search_pipeline, user_text, safe_name, user_id)
            await send_whatsapp_message(to=user_id, text=f"✅ Done! CV generated and saved in your output folder.")

    except Exception as e:
        await send_whatsapp_message(to=user_id, text=f"❌ An error occurred: {str(e)}")

    log_message_data(normalized_data, "[Agent pipeline executed]")

