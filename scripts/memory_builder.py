"""
scripts/memory_builder.py
Run this script manually whenever you update C-core/career_master.json.
Command to run from project root: python -m scripts.memory_builder
"""
import json
import chromadb
import os

def sync_memory():
    # 1. Read your manual JSON file[cite: 8]
    json_path = os.path.join(os.getcwd(), "C-core", "career_master.json")
    with open(json_path, "r", encoding="utf-8") as f:
        career_blocks = json.load(f)

    # 2. Connect to ChromaDB[cite: 8]
    db_path = os.path.join(os.getcwd(), "chroma_db")
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_or_create_collection("career_history")

    # 3. Sync everything to the database[cite: 8]
    documents = [block["text"] for block in career_blocks]
    ids = [block["id"] for block in career_blocks]
    
    # Safely handle metadata (ChromaDB requires strings, ints, or floats)[cite: 8]
    metadatas = [{"category": block.get("category", "General")} for block in career_blocks]

    collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
    print(f"Synced {len(career_blocks)} items to ChromaDB.")

if __name__ == "__main__":
    sync_memory()