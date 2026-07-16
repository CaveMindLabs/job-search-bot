"""
services/file_manager.py
Handles local file system searches and reading files for the WhatsApp bot.
"""
import os
import glob

def search_local_cvs(search_term):
    """Searches the O-output folder and its subfolders using flexible keyword matching."""
    os.makedirs("O-output", exist_ok=True)
    
    # Use recursive=True to check inside DEV and MGMT subfolders
    files = glob.glob("O-output/**/*.md", recursive=True)
    
    # Split the search term into individual words (ignoring empty strings)
    search_words = [word.lower() for word in search_term.split() if word.strip()]
    matches = []
    
    for f in files:
        filename_lower = os.path.basename(f).lower()
        
        # Check if ANY of the words in the search term exist in the filename
        # This allows "google software engineer" to successfully match "Google.md"
        if any(word in filename_lower for word in search_words):
            matches.append(os.path.basename(f))
            
    return matches

def get_cv_content(filename):
    """Retrieves the text content of a specific CV from any subfolder."""
    base_dir = "O-output"
    if not os.path.exists(base_dir):
        return None
        
    # Walk through the base directory and all subdirectories
    for root, dirs, files in os.walk(base_dir):
        if filename in files:
            filepath = os.path.join(root, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
                
    return None