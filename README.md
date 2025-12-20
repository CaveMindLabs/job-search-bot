# WhatsApp FastAPI Agent

A production-ready FastAPI boilerplate for building AI chat agents on the WhatsApp Cloud API using OpenAI. This project features per-user memory, tool-calling capabilities, secure integration with services like n8n, and comprehensive documentation for a smooth setup.

---

## Features

-   **Complete Webhook Handling**: Full implementation of the WhatsApp Cloud API webhook for receiving and replying to messages.
-   **Contextual Conversations**: Maintains a separate conversation history for each user, allowing for contextual, multi-turn interactions.
-   **AI Tool-Calling**: The LLM can use internal Python functions to answer questions (e.g., listing available models).
-   **Dynamic Model Selection**: Users can switch the OpenAI model for their specific chat using a simple command (`/Use model: "gpt-4o"`).
-   **Proactive Messaging API**: A secure, key-protected endpoint (`/whatsapp/send`) allows external services like n8n to send outbound messages.
-   **Background Processing**: Ensures reliability by immediately acknowledging webhooks and processing AI generation in the background.
-   **Production-Ready Guides**: Includes detailed documentation for setting up a permanent public URL with Cloudflare Tunnels and generating a stable, long-lived Meta API token.

---

## Core Architecture

The project is structured to separate concerns, making it clean, scalable, and easy to maintain. At a high level, an incoming WhatsApp message is processed in the background, passed to an AI service with memory, and the reply is sent back to the user.

For a detailed breakdown of the internal logic and step-by-step execution flows, see the [**Architecture and Flow Documentation**](./documentation/ARCHITECTURE_AND_FLOW.md).

### Project Structure Diagram
```plaintext
whatsapp-fastapi-agent/
├── .cloudflared/      # (Local) Cloudflare Tunnel configuration.
├── api/               # FastAPI routers and dependencies.
├── core/              # Core application settings and configuration.
├── documentation/     # Guides for setup, integration, and architecture.
├── models/            # Pydantic models for data validation.
├── services/          # Business logic (OpenAI, WhatsApp, Memory).
├── utils/             # Helper utilities (logging, normalization).
├── .env.example       # Environment variable template.
├── environment.yml    # Conda environment definition.
├── main.py            # Main FastAPI application entry point.
└── README.md          # Project overview and setup instructions.
```

---

## Getting Started

### 1. Prerequisites

-   A **Meta Business Account** and a **Developer App** with the WhatsApp product enabled.
-   An **OpenAI API Key**.
-   A public domain managed through **Cloudflare**.
-   **Conda** for environment management.
-   `cloudflared` CLI tool installed and authenticated.

### 2. Initial Setup

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/your-domain/whatsapp-fastapi-agent.git
    cd whatsapp-fastapi-agent
    ```

2.  **Create the Conda Environment:**
    ```bash
    conda env create -f environment.yml
    conda activate whatsapp-agent
    ```

3.  **Configure Environment Variables:**
    -   Copy the `.env.example` file to a new file named `.env`.
    -   Generate secure keys for `VERIFY_TOKEN` and `INTERNAL_API_KEY` using the commands in [`documentation/Secret_Keys_Generation_Commands.md`](./documentation/Secret_Keys_Generation_Commands.md).
    -   Generate a permanent `WHATSAPP_TOKEN` by following the guide in [`documentation/WHATSAPP_PERMANENT_TOKEN_GENERATION.md`](./documentation/WHATSAPP_PERMANENT_TOKEN_GENERATION.md).
    -   Fill in all the other required values (`PHONE_NUMBER_ID`, `OPENAI_API_KEY`, etc.).

4.  **Set up the Public Webhook URL:**
    -   Follow the one-time setup guide in [`documentation/CLOUDFLARE_WEBHOOK_SETUP.md`](./documentation/CLOUDFLARE_WEBHOOK_SETUP.md) to create a permanent Cloudflare Tunnel and link it to your Meta App.

### 3. Running the Application

You will need two separate terminals.

**Terminal 1: Start the FastAPI Server**
```bash
# In the project root directory
conda activate whatsapp-agent
uvicorn main:app --reload --port 8000
```

**Terminal 2: Start the Cloudflare Tunnel**
```bash
# In the project root directory
# (Ensure your config.yml is correctly configured first)
cloudflared tunnel --config ./.cloudflared/config.yml run <your-tunnel-name>
```

Your agent is now live and can receive messages from WhatsApp.

---

## Testing & Integration

### Local Testing
You can test the entire application flow without sending a real WhatsApp message by sending a simulated webhook request from your local machine. This is extremely useful for debugging.

For this test, the FastAPI server must be running (Terminal 1), but the Cloudflare Tunnel is not required.

#### Step 1: Prepare the Test Payload

Ensure you have a `test_payload.json` file in the root of your project with the following content.

> **Important:** Replace `YOUR_REAL_WA_ID` with your own personal WhatsApp number (the one verified for testing in the Meta dashboard), including the country code. This ensures the API call to send a reply succeeds.

```json
{
  "object": "whatsapp_business_account",
  "entry": [
    {
      "id": "2456257964",
      "changes": [
        {
          "value": {
            "messaging_product": "whatsapp",
            "metadata": {
              "display_phone_number": "66660007893",
              "phone_number_id": "YOUR_BUSINESS_PHONE_NUMBER_ID"
            },
            "contacts": [
              {
                "profile": { "name": "Local Test User" },
                "wa_id": "YOUR_REAL_WA_ID"
              }
            ],
            "messages": [
              {
                "from": "YOUR_REAL_WA_ID",
                "id": "wamid.your_test_message_id",
                "timestamp": "1701108242",
                "text": { "body": "Hello from a local test!" },
                "type": "text"
              }
            ]
          },
          "field": "messages"
        }
      ]
    }
  ]
}
```

#### Step 2: Send the Test Request

Open a **third terminal** (PowerShell is recommended on Windows) and run the following command to send the payload to your local server.

```powershell
# Ensure you are in the project's root directory
cd path\to\whatsapp-fastapi-agent
# Then run:
$headers = @{
    "Content-Type" = "application/json"
}

$body = Get-Content -Raw -Path .\test_payload.json

Invoke-WebRequest -Uri http://127.0.0.1:8000/whatsapp/webhook -Method POST -Headers $headers -Body $body
```

#### Step 3: Check the Logs

If the test is successful, you will see a `200 OK` response in your PowerShell terminal. More importantly, in your FastAPI server terminal (Terminal 1), you should see a series of logs confirming the entire flow:

1.  `INFO - Received webhook payload...`
2.  `INFO - Calling OpenAI for user...`
3.  `INFO - Successfully generated reply for user...`
4.  `INFO - Sending message to ...`
5.  `INFO - Message sent successfully to ...`
6.  `INFO - Logged message for user ...`

This confirms that the application logic is working correctly from end to end.

---

### n8n Integration
To send proactive messages from an n8n workflow, follow the detailed setup guide in [`documentation/N8N_INTEGRATION.md`](./documentation/N8N_INTEGRATION.md).
