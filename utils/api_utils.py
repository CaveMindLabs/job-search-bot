from tenacity import retry, wait_exponential, stop_after_attempt

# reraise=True ensures the actual API error is passed back to your pipeline
@retry(wait=wait_exponential(multiplier=2, min=2, max=10), stop=stop_after_attempt(3), reraise=True)
def run_crew_with_backoff(crew_instance):
    result = str(crew_instance.kickoff().raw).strip()
    
    # Sanity check: Catch silent failures where the agent hallucinates its own instructions
    if "JSON Format" in result or "Remember, formatting counts!" in result:
        raise Exception("Agent hallucination triggered by rate limits.")
        
    return result