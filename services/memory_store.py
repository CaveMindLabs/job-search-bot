# services/memory_store.py

from collections import defaultdict
from typing import List, Dict, Any
from datetime import datetime, timezone
from core.config import get_settings

def _user_data_factory():
    """
    Factory for creating a default user data structure.
    This is called ONLY when a new user is created.
    It now also initializes the chat history with a starting system message.
    """
    initial_model = get_settings().OPENAI_MODEL_NAME
    # Pre-populate the history with the initial context message
    initial_history = [
        {
            "role": "assistant",
            "content": f"(System notification: Conversation started with model {initial_model})"
        }
    ]
    return {
        "history": initial_history,
        "preferences": {
            "model": None # Default to None, so we use the system-wide default
        }
    }

class MemoryStore:
    """
    An in-memory store for conversation history and user preferences.
    Each user_id maps to a dictionary containing their message history and settings.
    """
    def __init__(self):
        # Use a defaultdict with our factory to auto-create user structures
        self.store = defaultdict(_user_data_factory)

    def set_user_preference(self, user_id: str, key: str, value: Any) -> None:
        """
        Sets a specific preference for a user (e.g., 'model').
        If the preference is 'model', it also adds a system notification to the history.
        """
        self.store[user_id]["preferences"][key] = value
        if key == "model":
            timestamp_str = datetime.now(timezone.utc).isoformat()
            self.add_message(
                user_id, 
                "assistant",
                f"[{timestamp_str}] System notification: Model successfully updated on user request to {value})"
            )

    def get_user_preference(self, user_id: str, key: str) -> Any | None:
        """Gets a specific preference for a user."""
        return self.store[user_id]["preferences"].get(key)

    def add_message(self, user_id: str, role: str, content: str) -> None:
        """
        Adds a new message to a user's history.
        If the role is 'user', it prepends the current UTC timestamp to the content.
        """
        if role == "user":
            timestamp_str = datetime.now(timezone.utc).isoformat()
            # Embed the timestamp directly into the content string for the model to see.
            final_content = f"[{timestamp_str}] {content}"
        else:
            final_content = content
        message = {
            "role": role,
            "content": final_content,
        }
        self.store[user_id]["history"].append(message)

    def get_history(self, user_id: str, limit: int = 30) -> List[Dict[str, str]]:
        """
        Retrieves the last 'limit' messages for a user.
        The history is already formatted correctly for the OpenAI API.
        """
        return self.store[user_id]["history"][-limit:]

# Create a singleton instance to be used across the application
memory_store = MemoryStore()
