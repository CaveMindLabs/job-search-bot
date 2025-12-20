# Project Architecture and Execution Flow

This document provides a detailed look at the project's structure and the step-by-step execution flow for handling incoming WhatsApp messages.

---

## 1. Project Structure

The project follows a standard FastAPI layout, separating concerns into distinct modules for clarity and maintainability.

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

## 2. Execution Flow

The application processes messages in the background to ensure the webhook responds to Meta's servers immediately. There are two primary flows depending on whether the LLM decides to use a tool.

### Flow A: Standard Chat Reply (No Tool Use)

This is the most common path, where a user sends a message and receives a direct conversational reply.

```mermaid
sequenceDiagram
    participant User
    participant WhatsApp
    participant Cloudflare
    participant FastAPI
    participant BackgroundTask
    participant OpenAIService
    participant MemoryStore
    participant WhatsAppService

    User->>+WhatsApp: Sends "Hello, how are you?"
    WhatsApp->>+Cloudflare: POST /whatsapp/webhook
    Cloudflare->>+FastAPI: Forwards POST request to localhost:8000

    Note over FastAPI: Endpoint `/whatsapp/webhook` in `api/whatsapp.py` receives the request.

    FastAPI->>FastAPI: 1. Parses and validates payload with Pydantic `WebhookPayload`.
    FastAPI->>FastAPI: 2. Normalizes the message data via `utils.normalization`.
    FastAPI->>BackgroundTask: 3. Schedules `process_and_reply` to run in the background.
    FastAPI-->>-Cloudflare: 4. Immediately returns HTTP 200 OK.
    Cloudflare-->>-WhatsApp: HTTP 200 OK

    Note over BackgroundTask: The background task now runs independently.

    BackgroundTask->>OpenAIService: Calls `generate_reply` with user message.
    OpenAIService->>MemoryStore: 1. `get_user_preference()` (to get the model).
    OpenAIService->>MemoryStore: 2. `get_history()` (to get conversation context).
    OpenAIService->>+OpenAI API: 3. Makes API call with system prompt + history + user message.
    OpenAI API-->>-OpenAIService: Returns a standard chat completion (e.g., "I'm doing well!").

    OpenAIService->>MemoryStore: 4. `add_message()` (to save user's "Hello...").
    OpenAIService->>MemoryStore: 5. `add_message()` (to save assistant's "I'm doing well!...").
    OpenAIService-->>BackgroundTask: Returns the final reply text.

    BackgroundTask->>WhatsAppService: Calls `send_whatsapp_message` with reply.
    WhatsAppService->>+WhatsApp: Sends "I'm doing well!" message via Graph API.
    WhatsApp-->>-User: Delivers reply message.
    
    Note over BackgroundTask: Finally, it logs the interaction.
    BackgroundTask->>BackgroundTask: Calls `utils.logging.log_message_data`.
```

### Flow B: Chat Reply with Tool Use (e.g., "what models can I use?")

This flow is triggered when the user's query causes the LLM to call the `list_available_models` tool. It involves two API calls to OpenAI.

```mermaid
sequenceDiagram
    participant User
    participant WhatsApp
    participant FastAPI
    participant BackgroundTask
    participant OpenAIService
    participant WhatsAppService

    User->>+WhatsApp: Sends "what models can I use?"
    WhatsApp-->>FastAPI: (Webhook forwarding via Cloudflare as before...)
    FastAPI->>BackgroundTask: Schedules `process_and_reply` and returns 200 OK.

    Note over BackgroundTask: Background task begins execution.

    BackgroundTask->>OpenAIService: Calls `generate_reply` with user message.
    OpenAIService->>+OpenAI API: **[First Call]** Sends prompt. The LLM decides to call the `list_available_models` tool.
    OpenAI API-->>-OpenAIService: Returns a response containing a `tool_calls` object.

    Note over OpenAIService: Detects the tool call request.

    OpenAIService->>OpenAIService: 1. Executes the local Python function `list_available_models()`.
    OpenAIService->>OpenAIService: 2. Formats the returned list into a user-friendly string.
    OpenAIService->>WhatsAppService: 3. **Sends list immediately** via `send_message_callback`.
    WhatsAppService->>+WhatsApp: Sends formatted model list to the user.
    WhatsApp-->>-User: Delivers the list of models.

    OpenAIService->>+OpenAI API: **[Second Call]** Sends the original history PLUS the tool execution result (e.g., "Function executed successfully").
    OpenAI API-->>-OpenAIService: Returns a final conversational reply (e.g., "I've just sent you the list of available models.").

    OpenAIService->>OpenAIService: 4. Updates memory with user message and final assistant reply.
    OpenAIService-->>BackgroundTask: Returns the final conversational reply.
    
    BackgroundTask->>WhatsAppService: Calls `send_whatsapp_message` with the final reply.
    WhatsAppService->>+WhatsApp: Sends "I've just sent you the list..."
    WhatsApp-->>-User: Delivers the second, final message.

    Note over BackgroundTask: Logs the full interaction.
    BackgroundTask->>BackgroundTask: Calls `utils.logging.log_message_data`.
```
