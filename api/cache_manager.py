import json
import os

CACHE_FILE = "api/cache_store.json"

def get_user_cache(user_id):
    if not os.path.exists(CACHE_FILE):
        return {}
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f).get(str(user_id), {})
        except json.JSONDecodeError:
            return {}

def update_user_cache(user_id, updates):
    all_cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            try:
                all_cache = json.load(f)
            except json.JSONDecodeError:
                pass
                
    user_str = str(user_id)
    if user_str not in all_cache:
        all_cache[user_str] = {}
        
    all_cache[user_str].update(updates)
    
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(all_cache, f, indent=4)