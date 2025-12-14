# services/memory_store.py

from collections import defaultdict
from typing import List, Dict

class MemoryStore:
    """
    A simple in-memory store for conversation history.
    Keys are user_ids, values are a list of message dicts.

    This is designed to be easily replaceable with a persistent store
    like Redis or a database without changing the service that uses it.
    """
    def __init__(self):
        self.store = defaultdict(list)

    def add_message(self, user_id: str, role: str, content: str) -> None:
        """Adds a new message to a user's history."""
        message = {"role": role, "content": content}
        self.store[user_id].append(message)

    def get_history(self, user_id: str, limit: int = 20) -> List[Dict[str, str]]:
        """
        Retrieves the last 'limit' messages for a user.
        Returns messages from oldest to newest.
        """
        return self.store[user_id][-limit:]

# Create a singleton instance to be used across the application
memory_store = MemoryStore()
