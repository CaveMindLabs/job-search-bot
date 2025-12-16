# utils/logging.py

import logging
from datetime import datetime, timezone 
from typing import List, Dict

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# In-memory list to store logs. In a real app, this would be a database,
# a file, or a service like Google Sheets.
IN_MEMORY_LOGS: List[Dict] = []

def log_message_data(normalized_data: dict, reply_text: str):
    """
    Logs inbound and outbound message data.
    """
    log_entry = {
        "server_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "inbound": normalized_data,
        "outbound": {"text": reply_text}
    }
    IN_MEMORY_LOGS.append(log_entry)
    logging.getLogger(__name__).info(f"Logged message for user {normalized_data['user_id']}")
    # For debugging, you can print the last 5 logs
    # print("--- LATEST LOGS ---")
    # for log in IN_MEMORY_LOGS[-5:]:
    #     print(log)
