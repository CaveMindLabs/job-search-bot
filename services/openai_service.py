# services/openai_service.py

import logging
from openai import AsyncOpenAI
from .memory_store import MemoryStore
from core.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)

# System prompt to define the assistant's personality and role
SYSTEM_PROMPT = """
You are a friendly and helpful WhatsApp assistant.
Your goal is to provide concise and accurate answers to user queries.
Keep your responses brief and suitable for a chat interface.
"""

# Initialize settings and OpenAI client
settings = get_settings()
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def list_available_models() -> list[str]:
    """
    Fetches the list of available GPT models from the OpenAI API.
    Filters for models that are compatible with the Chat Completions API.
    """
    try:
        models = await client.models.list()
        # Filter for models that are typically used for chat, you can adjust this filter
        chat_models = [
            model.id for model in models.data if "gpt" in model.id and "instruct" not in model.id
        ]
        return sorted(chat_models)
    except Exception as e:
        logger.error(f"Could not fetch models from OpenAI: {e}")
        return []

async def generate_reply(
    user_id: str, 
    user_text: str, 
    memory_store: MemoryStore,
    model_name: str | None = None
) -> str:
    """
    Generates a reply using OpenAI's Chat Completions API with conversation history.
    Uses a specified model or falls back to the default from settings.
    """
    try:
        # 1. Determine which model to use
        final_model = model_name or settings.OPENAI_MODEL_NAME
        logger.info(f"Using model '{final_model}' for user: {user_id}")

        # 2. Fetch conversation history from the memory store
        history = memory_store.get_history(user_id)

        # 3. Construct the message list for the API call
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ] + history + [
            {"role": "user", "content": user_text}
        ]

        # 4. Call the OpenAI API
        logger.info(f"Calling OpenAI for user: {user_id}")
        response = await client.chat.completions.create(
            model=final_model, # Use the determined model
            messages=messages,
            temperature=0.7,
        )

        assistant_reply = response.choices[0].message.content

        if not assistant_reply:
             raise ValueError("Received an empty reply from OpenAI.")

        # 5. Update memory with the new user message and assistant reply
        memory_store.add_message(user_id, "user", user_text)
        memory_store.add_message(user_id, "assistant", assistant_reply)

        logger.info(f"Successfully generated reply for user: {user_id}")
        return assistant_reply

    except Exception as e:
        logger.error(f"Error generating reply for user {user_id}: {e}")
        # Return a generic error message to the user
        return "I'm sorry, I encountered an issue and can't respond right now."
