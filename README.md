# WhatsApp AI Job Search & CV Agent

A production-ready FastAPI backend that connects WhatsApp to a multi-agent CrewAI swarm. This bot actively searches the web for job opportunities, extracts corporate culture data, learns from your feedback, and generates highly tailored Markdown resumes.

## 🛠️ Tech Stack
*   **Web Server:** FastAPI (Python)
*   **Agent Orchestration:** CrewAI
*   **LLM Engine:** Google Gemini (3.5 Flash / 3.5 Pro)
*   **Search Engine:** Serper.dev API
*   **Vector Database:** ChromaDB (Local SQLite)
*   **Tunneling:** ngrok (For Meta Webhook connection)
*   **Messaging:** Meta WhatsApp Cloud API

## 🤖 The Agent Team
The project utilizes 10 distinct AI agents, each strictly scoped to a specific task:
1.  **Router Agent:** Analyzes WhatsApp text to determine intent.
2.  **Prospector Agent:** Searches Google/LinkedIn for localized jobs matching qualifications.
3.  **Hunter Agent:** Finds the exact URL for a specific job request.
4.  **Extractor Agent:** Scrapes job postings into structured JSON.
5.  **Culture Scout Agent:** Scrapes company websites for core values and leadership principles.
6.  **Strategist Agent:** Maps career history and company culture to a targeted CV strategy.
7.  **Tailor Agent:** Drafts replacement text for CV template brackets.
8.  **Gatekeeper Agent:** Finalizes and saves the Markdown resume.
9.  **Feedback Analyzer Agent:** Distills user feedback into actionable database rules.
10. **Database Editor Agent:** Translates natural language into database modifications.
11. **Targeted Outreach:** Finds recruiters and hiring managers at specific companies on LinkedIn via Google search.
12. **Personalized Messaging:** Accepts a LinkedIn URL, a Job URL, and your CV, and drafts both a 300-character LinkedIn connection request and a longer InMail message.


## 🚀 Setup & Installation Instructions

### 1. Prerequisites
You must have the following accounts and tools installed:
*   **Python 3.10+**
*   **ngrok:** Installed globally on your system.
*   **Meta Developer Account:** With a WhatsApp Business app created.
*   **Gemini API Key:** From Google AI Studio.
*   **Serper API Key:** From Serper.dev.

### 2. Local Installation
1. Clone the repository:
   ```bash
   git clone [https://github.com/your-username/whatsapp-job-agent.git](https://github.com/your-username/whatsapp-job-agent.git)
   cd whatsapp-job-agent

Create and activate a virtual environment:
   python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

Install dependencies:
   pip install -r requirements.txt

3. Environment Variables
   Copy .env.example to .env and fill in your keys:
   Generate a VERIFY_TOKEN and INTERNAL_API_KEY (you can use openssl rand -base64 32 or any random password generator).
   Add your GEMINI_API_KEY and SERPER_API_KEY.
   Follow the guide in documentation/WHATSAPP_PERMANENT_TOKEN_GENERATION.md to get your Meta WHATSAPP_TOKEN.

4. Running the Bot
   Create a file named start_agent.bat in the root folder with the following contents to start your server and ngrok simultaneously:
      @echo off
      start "Uvicorn Server" cmd /k "call .venv\Scripts\activate && uvicorn main:app --reload"
      call .venv\Scripts\activate
      ngrok http 8000

**Note:** Copy the https://....ngrok-free.app URL and paste it into your Meta App's Webhook configuration, appending /whatsapp/webhook to the end.

## 📱 How to Use It (Commands & Pipelines)

Once online, send a natural language message to your WhatsApp bot. 

**1. "Search for jobs: [Query]"**
*   **Intent:** `SEARCH_JOBS`
*   **Pipeline:** Router -> Prospector

**2. "Create a CV for this link: [URL]"**
*   **Intent:** `CV`
*   **Pipeline:** Router -> Extractor -> Culture Scout -> Keyword Agent -> Strategist -> Tailor -> Gatekeeper

**3. "Review the [Search Term] CV for [URL]"**
*   **Intent:** `REVIEW_CV`
*   **Pipeline:** Router -> Reviewer Agent (ATS Scoring)

**4. "Find best CV for [URL]"**
*   **Intent:** `FIND_BEST_CV`
*   **Pipeline:** Router -> Reviewer Agent (Matchmaking)

**5. "Feedback: [Feedback]"**
*   **Intent:** `FEEDBACK`
*   **Pipeline:** Router -> Feedback Analyzer (Saves to ChromaDB)

**6. "Delete/Edit rule [Rule Number]"**
*   **Intent:** `DB_MANAGE`
*   **Pipeline:** Router -> Database Editor

**7. "Get CV: [Filename]"**
*   **Intent:** `RETRIEVE`
*   **Pipeline:** Router -> File Manager Service (Sends file to WhatsApp)


Developer: Matan Eshel
Engineered to bridge the gap between complex LLM orchestration and seamless daily operations.