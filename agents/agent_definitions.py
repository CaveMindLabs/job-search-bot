from crewai import Agent
from agents.config import gemini_flash, gemini_pro, scrape_tool, search_tool
import time

def agent_throttle_callback(step_output):
    """
    Forces a 2.5-second pause after every single ReAct loop step (Thought/Action/Observation)
    to prevent Google's load balancers from registering the burst as an attack.
    """
    time.sleep(2.5)

prospector_agent = Agent(
    role="Technical Recruiter & Job Prospector",
    goal="Find highly relevant, active job posting URLs based on the candidate's qualifications.",
    backstory="You are an expert headhunter. You use advanced search operators (like site:linkedin.com/jobs) to find roles that perfectly match a candidate's background.",
    llm=gemini_flash,
    verbose=True
)

hunter_agent = Agent(
    role="Job Hunter",
    goal="Find the exact active URL for a specific job posting.",
    backstory="You are a technical sourcer. You use Google Search to find active job listings.",
    tools=[search_tool],
    llm=gemini_flash,
    allow_delegation=False, # Stops internal hidden requests
    max_iter=3,             # Forces it to finish after 3 attempts
    step_callback=agent_throttle_callback,
    verbose=True
)

extractor_agent = Agent(
    role="Job Posting Extractor",
    goal="Scrape job postings and structure the content into JSON.",
    backstory="You strip away website boilerplate and extract core job details.",
    tools=[scrape_tool],
    llm=gemini_flash,
    allow_delegation=False, # Stops internal hidden requests
    max_iter=3,             # Forces it to finish after 3 attempts
    step_callback=agent_throttle_callback,
    verbose=True
)

router_agent = Agent(
    role="Job Classification Router",
    goal="Determine if a job is primarily DEV (software engineering) or MGMT (project/product management).",
    backstory="You are a fast, precise binary classifier. You read a job description and output exactly one word: 'DEV' or 'MGMT'.",
    llm=gemini_flash,
    allow_delegation=False, # Stops internal hidden requests
    max_iter=3,             # Forces it to finish after 3 attempts
    step_callback=agent_throttle_callback,
    verbose=False
)

culture_scout = Agent(
    role="Corporate Culture Analyst",
    goal="Find and extract a company's official core values, mission statement, or leadership principles.",
    backstory="You are an expert in corporate employer branding. You search the web to find official company values (like Amazon's Leadership Principles or Google's 'Ten things we know to be true') so candidates can tailor their applications.",
    tools=[search_tool, scrape_tool],
    llm=gemini_flash,
    allow_delegation=False,
    max_iter=3,
    step_callback=agent_throttle_callback,
    verbose=True
)

keyword_agent = Agent(
    role="ATS Keyword Analyzer",
    goal="Identify and extract the 10-15 most critical technical keywords and domain terms from the job description.",
    backstory="You are an ATS optimization expert. You identify the exact terminology hiring managers look for without resorting to unnatural keyword stuffing.",
    llm=gemini_flash,
    allow_delegation=False,
    max_iter=3,
    step_callback=agent_throttle_callback,
    verbose=True
)

# --- REASONING AGENTS UPGRADED TO PRO ---

strategist = Agent(
    role="Career Strategist",
    goal="Map user history to job requirements to generate a CV strategy.",
    backstory="You optimize resumes for ATS and hiring managers.",
    llm=gemini_pro,
    allow_delegation=False, # Stops internal hidden requests
    max_iter=3,             # Forces it to finish after 3 attempts
    step_callback=agent_throttle_callback,
    verbose=True
)

tailor = Agent(
    role="Resume Tailor",
    goal="Draft targeted replacement markdown text for CV brackets.",
    backstory="You write concise, impactful bullet points.",
    llm=gemini_pro,
    allow_delegation=False, # Stops internal hidden requests
    max_iter=3,             # Forces it to finish after 3 attempts
    step_callback=agent_throttle_callback,
    verbose=True
)

gatekeeper = Agent(
    role="Core Identity & Contradiction Auditor",
    goal="Ensure the final resume is perfectly formatted and free of core historical contradictions.",
    backstory="You are a meticulous legal and corporate auditor. You review drafted resumes against raw career history. You allow creative framing and plausible achievement embellishments, but you have zero tolerance for structural lies, such as changing official job titles, fabricating employment dates, or claiming direct employment at client or partner companies.",
    llm=gemini_pro,
    allow_delegation=False, # Stops internal hidden requests
    max_iter=3,             # Forces it to finish after 3 attempts
    step_callback=agent_throttle_callback,
    verbose=True
)

reviewer_agent = Agent(
    role="ATS Auditor & Technical Recruiter",
    goal="Score a CV against a job description from 1-10 and provide actionable feedback.",
    backstory="You are a senior technical recruiter and ATS algorithm expert. You evaluate resumes based on hard skills match, keyword density, and quantified experience alignment.",
    llm=gemini_pro,
    allow_delegation=False,
    max_iter=3,
    step_callback=agent_throttle_callback,
    verbose=True
)

cv_editor_agent = Agent(
    role="CV Editor & Formatter",
    goal="Apply review recommendations to a Markdown CV seamlessly.",
    backstory="You are an expert resume writer. You take existing Markdown CVs and update the text strictly based on reviewer feedback while keeping the Markdown layout perfectly intact.",
    llm=gemini_pro,
    allow_delegation=False, # Stops internal hidden requests
    max_iter=3,             # Forces it to finish after 3 attempts
    step_callback=agent_throttle_callback,
    verbose=True
)

key_people_finder = Agent(
    role="Technical Sourcer & LinkedIn Boolean Expert",
    goal="Find LinkedIn profiles of recruiters, HR, and engineering managers for a specific company and role in Israel.",
    backstory="You are a master of Google Dorking for LinkedIn. You know how to find the hidden hiring managers and talent acquisition staff by searching site:linkedin.com/in/. You always return a clean list of names, titles, and URLs.",
    tools=[search_tool],
    llm=gemini_pro,
    allow_delegation=False, # Stops internal hidden requests
    max_iter=3,             # Forces it to finish after 3 attempts
    step_callback=agent_throttle_callback,
    verbose=True
)

personal_message_drafter = Agent(
    role="Executive Communications Strategist",
    goal="Draft highly personalized, professional outreach messages to recruiters and hiring managers.",
    backstory="You are an expert at cold outreach. You find common ground between candidates and recruiters (e.g., shared alma mater, prior industry, mutual interests) and write compelling, concise messages. You always draft two versions: a strict 300-character LinkedIn connection note, and a slightly longer InMail/Email message.",
    tools=[search_tool],
    llm=gemini_pro,
    allow_delegation=False, # Stops internal hidden requests
    max_iter=3,             # Forces it to finish after 3 attempts
    step_callback=agent_throttle_callback,
    verbose=True
)