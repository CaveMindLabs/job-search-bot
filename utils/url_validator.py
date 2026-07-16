import re
import requests

def validate_and_filter_urls(text):
    """
    Finds all HTTP/HTTPS URLs in a text block, pings them, 
    and appends a warning if the link is broken.
    """
    # Regex pattern to identify URLs in the raw text
    url_pattern = re.compile(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s\])"\']+')
    urls = set(url_pattern.findall(text)) # Use a set to avoid checking duplicates
    
    if not urls:
        return text
        
    # Mask the script as a standard browser to avoid basic bot blocks
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    
    for url in urls:
        try:
            # Using GET instead of HEAD as some strict servers reject HEAD requests
            response = requests.get(url, headers=headers, timeout=5, allow_redirects=True)
            
            # If the server returns a client or server error (400+)
            if response.status_code >= 400:
                text = text.replace(url, f"{url} [⚠️ Broken Link: {response.status_code}]")
        except requests.RequestException:
            # If the request times out or the domain doesn't exist
            text = text.replace(url, f"{url} [⚠️ Broken Link: Connection Failed]")
            
    return text